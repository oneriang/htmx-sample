import os
import re
import uvicorn
import json
from pathlib import Path

from fastapi import FastAPI, Response, Request, Form, Depends, HTTPException, status
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.security import OAuth2PasswordBearer
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.responses import HTMLResponse
from fastapi.responses import RedirectResponse
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi import UploadFile, File
from fastapi.middleware.cors import CORSMiddleware

from sqlalchemy import create_engine, MetaData, Table, select, insert, update, delete, inspect, or_, and_, func, desc, asc
from sqlalchemy.orm import sessionmaker, class_mapper
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.sql import expression
from sqlalchemy.sql.sqltypes import String, Integer, DateTime, Date, Boolean, Enum
from sqlalchemy import inspect, String, Integer, Float, DateTime, Date, Boolean, Enum

from passlib.context import CryptContext
from pydantic import BaseModel, Field
from typing import Dict, Any, List, Union, Optional
from jinja2 import Template, Environment
from jinja2 import Environment, FileSystemLoader

from urllib.parse import urlparse, parse_qs, urlunparse, urlencode

from jose import JWTError, jwt
from datetime import datetime, timedelta
from functools import wraps

import pprint
import yaml
import logging
import copy

import gv as gv
import transaction_module
from transaction_module import convert_value, TransactionModule

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 允许所有来源，您可以根据需要指定特定的源
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory="static"), name="static")
# app.mount("/files", StaticFiles(directory="files"), name="files")
app.mount("/uploaded", StaticFiles(directory="uploaded"), name="uploaded")

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

templates = Jinja2Templates(directory="templates")
# 添加 min 函数到模板上下文
templates.env.globals['min'] = min
templates.env.globals['site_name'] = '6666'

# Database connection configuration
DATABASE_URL = "sqlite:///./cms.db"
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
metadata = MetaData()
# Reflect existing database tables
metadata.reflect(bind=engine, views=True)

db = SessionLocal()

TM = TransactionModule(engine = engine, db = db, metadata = metadata)

gv.BASE_HTML = None
gv.HTML_TEMPLATES = None
gv.YAML_CONFIG = None
gv.icons = None
gv.classes = None
gv.model = {}
gv.models = []

def init():
  
  ConfigManager.load_data()
  
  
  gv.tables = DatabaseManager.get_tables()
  
  DatabaseManager.generate_all_configs(engine)
  
  pass

@app.api_route("/{any_path:path}", response_class=HTMLResponse)
async def universal_handler(any_path: str, request: Request):

    # # 获取 HTTP 方法
    # http_method = request.method

    # # 判断请求方法
    # if http_method == "GET":
    #     pass
    #     #return f"Received a GET request at path: {any_path}"
    # #elif http_method == "POST":
    # #    pass
    # #    #eturn f"Received a POST request at path: {any_path}"
    # elif http_method == "PUT":
    #     return f"Received a PUT request at path: {any_path}"
    # elif http_method == "DELETE":
    #     return await delete_blog_post(request)
    #     #return f"Received a DELETE request at path: {any_path}"
    # elif http_method == "PATCH":
    #     return f"Received a PATCH request at path: {any_path}"
    # else:
    #     return f"Received an unknown method ({http_method}) at path: {any_path}"
    
    full_path = request.url.path

    path_parts = full_path.strip("/").split("/")  # 分解路径为列表
    
    if request.url.path == '/':
        return await CustomRenderer.get(request)
    
    if request.url.path == '/api/blog/post/comments':
        return await BlogManager.get_blog_post_comments(request)
    
    if request.url.path == '/api/blog/categories':
        return await BlogManager.get_blog_categories(request)
    
    if request.url.path == '/api/blog/tags':
        return await BlogManager.get_blog_tags(request)

    if request.url.path == '/api/blog/users':
        return await BlogManager.get_blog_users(request)

    if request.url.path == '/component':
        return await rendered_component(request)
   
    if request.url.path == '/edit':
        return await edit_form(request)

  #if request.url.path == '/blog/post/comment':
  #      return await post_blog_post_comment(request)

    if len(path_parts) > 1 and path_parts[0] == 'api':
        if len(path_parts) > 2 and path_parts[1] == 'blog' and path_parts[2] == 'posts':
            return await CustomRenderer.get_posts(request)
        elif len(path_parts) > 2 and path_parts[1] == 'blog' and path_parts[2] == 'post':
            return await CustomRenderer.get_post(request)
  
    if len(path_parts) == 1:
        if path_parts[0] == 'blog':
            return await CustomRenderer.get_blog(request)
        elif path_parts[0] == 'settings':
            return await CustomRenderer.get(request)
    elif len(path_parts) > 1 and path_parts[0] == 'blog' and path_parts[1] == 'posts':
            return await CustomRenderer.get_blog(request)
    elif len(path_parts) > 1 and path_parts[0] == 'blog' and path_parts[1] == 'settings':
            return await CustomRenderer.get(request)
    elif len(path_parts) > 1 and path_parts[0] == 'blog' and path_parts[1] == 'about':
            return await CustomRenderer.get(request)

    return full_path

class BlogManager:
  
    @app.post("/blog/post", response_class=HTMLResponse)
    @staticmethod
    async def post_blog_post(request: Request):
        form_data = await request.form()
        file = form_data.get('featured_image')
    
        result = TM.execute_transactions(
                    transaction_name = 'create_post',
                    params={
                      'title': form_data['title'],
                      'slug': "slug",
                      'content': form_data['content'],
                      'status': form_data['status'],
                      #'file': form_data['featured_image']
                      'visibility': form_data['visibility'],
                      'category_id': form_data['category_id'],
                      'author_id': form_data['author_id'],
                      "file": file,
                      "file_name": file.filename,
                      "folder_path": "./uploaded"
                    },
                    config_file="cms.yaml"
                )
                
        headers = {"HX-Trigger": "newPost"}
        return HTMLResponse(content='ok', headers=headers)
    
    @app.put("/blog/post", response_class=HTMLResponse)
    @staticmethod
    async def put_blog_post(request: Request):
        form_data = await request.form()
        file = form_data.get('featured_image')
        
        result = TM.execute_transactions(
                    transaction_name = 'update_post',
                    params={
                        'id': form_data['id'],
                        'title': form_data['title'],
                        'content': form_data['content'],
                        'status': form_data['status'],
                        'visibility': form_data['visibility'],
                        'category_id': form_data['category_id'],
                        'author_id': form_data['author_id'],
                        "file": file,
                        "file_name": file.filename,
                        "folder_path": "./uploaded"
                    },
                    config_file="cms.yaml"
                )
                
        headers = {"HX-Trigger": "updatePost"}
        return HTMLResponse(content='ok', headers=headers)
    
    #@app.delete("/blog/posts", response_class=HTMLResponse)
    @staticmethod
    async def delete_blog_post(request: Request):
        print('blog_post_delete')
        query_params = dict(request.query_params)
    
        result = TM.execute_transactions(
                    transaction_name = 'delete_post',
                    params={
                      'id': query_params['post_id']
                    },
                    config_file="cms.yaml"
                )
                
        headers = {"HX-Trigger": "deletePost"}
        return HTMLResponse(content='ok', headers=headers)
    
    @app.post("/blog/post/comment", response_class=HTMLResponse)
    @staticmethod
    async def post_blog_post_comment(request: Request):
        
        form_data = await request.form()
        
        result = TM.execute_transactions(
                    transaction_name = 'add_comment',
                    params={
                      'post_id': form_data['post_id'],
                      # 'parent_id': form_data['parent_id'],
                      # 'user_id': form_data['user_id'],
                      'content': form_data['content']
                    },
                    config_file="cms.yaml"
                )
                
        headers = {"HX-Trigger": "newPostComment"}
        return HTMLResponse(content='ok', headers=headers)
    
    @app.get("/blog/post/comments", response_class=HTMLResponse)
    @staticmethod
    async def get_blog_post_comments(request: Request):
        
        gv.request = request
     
        if "HX-Request" in request.headers:
            pass
          
        query_params = dict(request.query_params)
    
        search_term = str(query_params['search_term']) if 'search_term' in query_params else ''
        page_size = int(query_params['page_size']) if 'page_size' in query_params else 5
        page_number = int(query_params['page_number']) if 'page_number' in query_params else 1
        post_id = int(query_params['post_id']) if 'post_id' in query_params else None
    
        result = TM.execute_transactions(
                    transaction_name = 'get_post_comments',
                    params={
                        'search_term': '%' + search_term + '%',
                        'limit': page_size,
                        'offset': (page_number - 1) * page_size,
                        'post_id': post_id
                    },
                    config_file="cms.yaml"
                )
        
        page_config = PageRenderer.load_page_config('blog_config.yaml')
    
        gv.component_dict['comment']['data'] = gv.data
        
        h = generate_html(gv.component_dict['comment'])
        
        return HTMLResponse(content=h)
        
    @app.get("/blog/categories", response_class=HTMLResponse)
    @staticmethod
    async def get_blog_categories(request: Request):
        
        gv.request = request
     
        if "HX-Request" in request.headers:
            pass
          
        query_params = dict(request.query_params)
    
        search_term = str(query_params['search_term']) if 'search_term' in query_params else ''
        page_size = int(query_params['page_size']) if 'page_size' in query_params else 5
        page_number = int(query_params['page_number']) if 'page_number' in query_params else 1
    
        result = TM.execute_transactions(
                    transaction_name = 'get_categories',
                    params={
                        'search_term': '%' + search_term + '%',
                        'limit': page_size,
                        'offset': (page_number - 1) * page_size
                    },
                    config_file="cms.yaml"
                )
        
        page_config = PageRenderer.load_page_config('settings_config.yaml')
    
        gv.component_dict['categorie']['data'] = gv.data
    
        h = PageRenderer.generate_html(gv.component_dict['categorie'])
        
        return HTMLResponse(content=h)
        
    @app.post("/blog/categorie", response_class=HTMLResponse)
    @staticmethod
    async def post_blog_categorie(request: Request):
        form_data = await request.form()
        
        result = TM.execute_transactions(
                    transaction_name = 'add_categorie',
                    params={
                      'name': form_data['name'],
                      'slug': form_data['slug'],
                      'description': form_data['description']
                    },
                    config_file="cms.yaml"
                )
                
        headers = {"HX-Trigger": "newBlogCategorie"}
        return HTMLResponse(content='ok', headers=headers)
    
    @app.get("/blog/tags", response_class=HTMLResponse)
    @staticmethod
    async def get_blog_tags(request: Request):
        
        gv.request = request
     
        if "HX-Request" in request.headers:
            pass
          
        query_params = dict(request.query_params)
    
        search_term = str(query_params['search_term']) if 'search_term' in query_params else ''
        page_size = int(query_params['page_size']) if 'page_size' in query_params else 5
        page_number = int(query_params['page_number']) if 'page_number' in query_params else 1
    
        result = TM.execute_transactions(
                    transaction_name = 'get_tags',
                    params={
                        'search_term': '%' + search_term + '%',
                        'limit': page_size,
                        'offset': (page_number - 1) * page_size
                    },
                    config_file="cms.yaml"
                )
        
        page_config = PageRenderer.load_page_config('settings_config.yaml')
    
        gv.component_dict['tag']['data'] = gv.data
        
        h = PageRenderer.generate_html(gv.component_dict['tag'])
        
        return HTMLResponse(content=h)
        
    @app.post("/blog/tag", response_class=HTMLResponse)
    @staticmethod
    async def post_blog_tag(request: Request):
        form_data = await request.form()
        
        result = TM.execute_transactions(
                    transaction_name = 'add_tag',
                    params={
                      'name': form_data['name'],
                      'slug': form_data['slug'],
                      'description': form_data['description']
                    },
                    config_file="cms.yaml"
                )
                
        headers = {"HX-Trigger": "newBlogTag"}
        return HTMLResponse(content='ok', headers=headers)
    
    @app.get("/blog/users", response_class=HTMLResponse)
    @staticmethod
    async def get_blog_users(request: Request):
        
        gv.request = request
     
        if "HX-Request" in request.headers:
            pass
          
        query_params = dict(request.query_params)
    
        search_term = str(query_params['search_term']) if 'search_term' in query_params else ''
        page_size = int(query_params['page_size']) if 'page_size' in query_params else 5
        page_number = int(query_params['page_number']) if 'page_number' in query_params else 1
    
        result = TM.execute_transactions(
                    transaction_name = 'get_users',
                    params={
                        'search_term': '%' + search_term + '%',
                        'limit': page_size,
                        'offset': (page_number - 1) * page_size
                    },
                    config_file="cms.yaml"
                )
        
        page_config = PageRenderer.load_page_config('settings_config.yaml')
    
        gv.component_dict['user']['data'] = gv.data
        
        h = PageRenderer.generate_html(gv.component_dict['user'])
        
        return HTMLResponse(content=h)
        
    @app.post("/blog/user", response_class=HTMLResponse)
    @staticmethod
    async def post_blog_user(request: Request):
        form_data = await request.form()
        result = TM.execute_transactions(
                    transaction_name = 'add_user',
                    params={
                      'username': form_data['username'],
                      'display_name': form_data['display_name'],
                      'email': form_data['email'],
                      'password_hash': form_data['password_hash']
                    },
                    config_file="cms.yaml"
                )
                
        headers = {"HX-Trigger": "newBlogUser"}
        return HTMLResponse(content='ok', headers=headers)

class CURDManager:
      
    @app.get("/create", response_class=HTMLResponse)
    @staticmethod
    async def create_form(request: Request):
        gv.request = request
    
        table_name = None
        id = None
          
        query_params = dict(request.query_params)
    
        if 'table_name' in query_params:
          table_name = query_params['table_name']
    
        if 'id' in query_params:
          id = query_params['id']
    
        if table_name is None:
          table_name = 'users'
        
        table_config = ConfigManager.get_table_config(table_name)
        
        primary_key = None
        
        
        if True:
          
            component_id = None
        
            if 'component_id' in query_params:
              component_id = query_params['component_id']
            
            if component_id is None:
              component_id = 'form_create'
              
            PageRenderer.load_page_config()
    
            gv.component_dict[component_id]['config'] = {
                'table_name':table_name,
                'id':id,
                'data': {},
                'primary_key':primary_key,
                'table_config':table_config
            }
            
            return generate_html(gv.component_dict[component_id])
            
        raise HTTPException(status_code=404, detail="Item not found")
    
    @app.post("/create/{table_name}")
    @staticmethod
    async def create_item(table_name: str, request: Request):
        table = None
        if table_name in metadata.tables:
            table = metadata.tables[table_name]
        if table is None:
            raise HTTPException(status_code=404, detail="Table not found")
    
        form_data = await request.form()
        data = {key: value for key, value in form_data.items() if key in table.columns.keys()}
        
        table_config = ConfigManager.get_table_config(table_name)
        
        for c in table_config['columns']:
          if c['primary_key'] == 1:
            if 'autoincrement' in c and c['autoincrement'] == True:
              data[c['name']] = None
    
        data_copy = copy.deepcopy(data)
        
        for key in data_copy:
            auto_update = False
            for c in table_config['columns']:
                if key == c['name']:
                    if 'auto_update' in c.keys():
                        if c['auto_update'] == True:
                            auto_update = True
                            break
                            
            if auto_update:
                data[key] = datetime.now()
            else:
                data[key] = convert_value(table.c[key].type, data[key])
                
        try:
            with SessionLocal() as session:
                stmt = insert(table).values(**data)
                session.execute(stmt)
                session.commit()
            return templates.TemplateResponse("table_content.html", {
                "request": request,
                "table_name": table_name,
                "columns": table.columns.keys(),
                "rows": session.execute(select(table)).fetchall(),
                "primary_key": ConfigManager.get_primary_key(table),
                "page": 1,
                "page_size": 10,
                "total_items": session.execute(select(func.count()).select_from(table)).scalar(),
                "total_pages": 1,
                "search": "",
            })
        except SQLAlchemyError as e:
            return {"success": False, "message": str(e)}
    
    @app.get("/edit", response_class=HTMLResponse)
    @staticmethod
    async def edit_form(request: Request):
        gv.request = request
    
        table_name = None
        id = None
          
        query_params = dict(request.query_params)
    
        if 'table_name' in query_params:
          table_name = query_params['table_name']
    
        if 'id' in query_params:
          id = query_params['id']
    
        if table_name is None:
          table_name = 'users'
        
        if id is None:
          id = 22
    
        table_config = ConfigManager.get_table_config(table_name)
        table = metadata.tables[table_name]
        
        primary_key = next((c['name'] for c in table_config['columns'] if c['primary_key'] == 1), None)
    
        if primary_key is None:
            primary_key = ConfigManager.get_primary_key(table)
         
        with SessionLocal() as session:
            stmt = select(table).where(getattr(table.c, primary_key) == id)
            result = session.execute(stmt).fetchone()._asdict()
        
        if result:
          
            data = dict(result)
            
            component_id = None
        
            if 'component_id' in query_params:
              component_id = query_params['component_id']
            
            if component_id is None:
              component_id = 'form_edit'
              
            PageRenderer.load_page_config()
    
            gv.component_dict[component_id]['config'] = {
                'table_name':table_name,
                'id':id,
                'data':data,
                'primary_key':primary_key,
                'table_config':table_config
            }
            
            return generate_html(gv.component_dict[component_id])
            
        raise HTTPException(status_code=404, detail="Item not found")
    
    @app.post("/edit/{table_name}/{id}")
    @staticmethod
    async def edit_item(table_name: str, id: str, request: Request):
    
        table = None
        if table_name in metadata.tables:
            table = metadata.tables[table_name]
        if table is None:
            raise HTTPException(status_code=404, detail="Table not found")
    
        primary_key = ConfigManager.get_primary_key(table)
        form_data = await request.form()
        data = {key: value for key, value in form_data.items() if key in table.columns.keys()}
        
        table_config = ConfigManager.get_table_config(table_name)
    
        data_copy = copy.deepcopy(data)
        
        for key in data_copy:
            auto_update = True
            for c in table_config['columns']:
                if key == c['name']:
                    if 'auto_update' in c.keys():
                        if c['auto_update'] == False:
                            auto_update = False
                            break
                            
            if auto_update:
                data[key] = convert_value(table.c[key].type, data[key])
            else:
                del data[key]
                
        try:
            with SessionLocal() as session:
                stmt = update(table).where(getattr(table.c, primary_key) == id).values(**data)
                session.execute(stmt)
                session.commit()
                return ''
                
        except SQLAlchemyError as e:
            return {"success": False, "message": str(e)}
    
    @app.get("/delete", response_class=HTMLResponse)
    @staticmethod
    async def delete_form(request: Request):
        gv.request = request
    
        table_name = None
        id = None
          
        query_params = dict(request.query_params)
    
        if 'table_name' in query_params:
          table_name = query_params['table_name']
    
        if 'id' in query_params:
          id = query_params['id']
    
        if table_name is None:
          table_name = 'users'
    
        table_config = ConfigManager.get_table_config(table_name)
        
        table = metadata.tables[table_name]
    
        primary_key = ConfigManager.get_primary_key(table)
         
        with SessionLocal() as session:
            stmt = select(table).where(getattr(table.c, primary_key) == id)
            result = session.execute(stmt).fetchone()._asdict()
        
        if result:
          
            data = dict(result)
            
            component_id = None
        
            if 'component_id' in query_params:
              component_id = query_params['component_id']
            
            if component_id is None:
              component_id = 'form_delete'
              
            PageRenderer.load_page_config()
    
            gv.component_dict[component_id]['config'] = {
                'table_name':table_name,
                'id':id,
                'data':data,
                'primary_key':primary_key,
                'table_config':table_config
            }
            
            return generate_html(gv.component_dict[component_id])
            
        raise HTTPException(status_code=404, detail="Item not found")
    
    @app.post("/delete/{table_name}/{id}")
    @staticmethod
    async def delete_item(table_name: str, id: str):
    
        table = None
        if table_name in metadata.tables:
            table = metadata.tables[table_name]
        if table is None:
            raise HTTPException(status_code=404, detail="Table not found")
    
        primary_key = ConfigManager.get_primary_key(table)
        
        try:
            with SessionLocal() as session:
                stmt = delete(table).where(getattr(table.c, primary_key) == id)
                session.execute(stmt)
                session.commit()
            # return {"success": True, "message": "Item deleted successfully"}
            return "Item deleted successfully"
        except SQLAlchemyError as e:
            return {"success": False, "message": str(e)}
  
class ConfigManager:
    """FastAPI 配置类，存储全局变量"""
    '''
    app = FastAPI()

    # 允许 CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # 模板引擎
    templates = Jinja2Templates(directory="templates")
    app.mount("/static", StaticFiles(directory="static"), name="static")

    # 全局变量
    
    # JWT 相关设置
    SECRET_KEY = "your-secret-key"
    ALGORITHM = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES = 30
    
    # 设置密码哈希
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

    '''
    
    @staticmethod
    def load_data_from_html(filename: str) -> Optional[str]:
        try:
            with open(filename, "r", encoding="utf-8") as file:
                return file.read()
        except IOError as e:
            logging.error(f"Error loading data from {filename}: {e}")
            return None
    
    @staticmethod
    def load_data_from_yaml(filename: str) -> Optional[Dict[str, Any]]:
        try:
            if filename is None:
                filename = 'main_config.yaml'
            with open(filename, "r", encoding="utf-8") as file:
                return yaml.safe_load(file)
        except (IOError, yaml.YAMLError) as e:
            logging.error(f"Error loading YAML data from {filename}: {e}")
            return None
    
    @staticmethod
    def load_data():
        
        if gv.BASE_HTML:
            pass
        else:
            gv.BASE_HTML = ConfigManager.load_data_from_html('base_html.html')
        
        if gv.HTML_TEMPLATES:
            pass
        else:
            gv.HTML_TEMPLATES = ConfigManager.load_data_from_yaml('html_templates.yaml')
        
        if gv.YAML_CONFIG:
            pass
        else:
            gv.YAML_CONFIG = ConfigManager.load_data_from_yaml('main_config.yaml')
    
        if gv.icons:
            pass
        else:
            gv.icons = gv.HTML_TEMPLATES.get('icons', {})
        
        if gv.classes:
            pass
        else:
            gv.classes = gv.HTML_TEMPLATES.get('classes', {})
  
    @staticmethod
    def get_table_config(table_name=None):
    
        request = gv.request
        
        search_params = {}
        if request:
          # Get all query parameters
          search_params = dict(request.query_params)
          if 'table_name' in search_params:
            table_name = search_params['table_name']
            
        if table_name is None:
          table_name = 'users'
          
        with open(f'table_configs/{table_name}_config.yaml', 'r') as f:
            config = yaml.safe_load(f)
            config['component_id'] = 'main_data_table'
            return config
  
    @staticmethod
    def get_primary_key(table):
        try:
          return next(iter(table.primary_key.columns)).name
        except Exception as e:
          return None

class PageRenderer:
    """页面渲染管理类"""
    templates_env = Environment(loader=FileSystemLoader("templates"))
    
    @staticmethod
    def load_data_from_yaml(filename: str) -> Optional[Dict[str, Any]]:
        try:
            with open(filename, "r", encoding="utf-8") as file:
                return yaml.safe_load(file)
        except Exception as e:
            logger.error(f"Error loading YAML data: {e}")
            return None

    @staticmethod
    def render_template(template_name: str, context: dict):
        template = PageRenderer.templates_env.get_template(template_name)
        return template.render(**context)
    
        
    # 辅助函数：解析组件引用
    @staticmethod
    def resolve_component(comp):
        if isinstance(comp, dict) and '$ref' in comp:
            return gv.component_dict[comp['$ref']]
        return comp
    
    # 修改加载配置函数
    @staticmethod
    def load_page_config(config_name = None) -> Dict[str, Any]:
        # config = yaml.safe_load(YAML_CONFIG)
        gv.YAML_CONFIG = ConfigManager.load_data_from_yaml(config_name)
        config = copy.deepcopy(gv.YAML_CONFIG)
        # # # print((config)
        gv.component_dict = {
            comp['id']: comp 
            for comp in config.get('component_definitions', {}).values()
        }
        
        def resolve_components(components):
            resolved = []
            for comp in components:
                if isinstance(comp, dict) and '$ref' in comp:
                    resolved.append(PageRenderer.resolve_component(comp))
                elif isinstance(comp, dict) and 'children' in comp:
                    resolved_comp = comp.copy()
                    resolved_comp['children'] = PageRenderer.resolve_components(comp['children'])
                    resolved.append(resolved_comp)
                else:
                    resolved.append(comp)
            return resolved
    
        config['components'] = resolve_components(config['components'])
        
        return config
    
    @staticmethod
    def generate_html(component: Dict[str, Any]) -> str:
    
        try:
            
            if 'type' not in component:
                component['type'] = 'div'
    
            for key in ['config', 'data', 'value', 'files']:
                if key in component and isinstance(component[key], str):
                    if component[key] in globals():
                        component[key] = globals()[component[key]]()
            
            if 'cols' in component:
                for key in component['cols']:
                    if component['id'] == 'form_comment':
    
                        if 'value' in component['cols'][key]:
                            value = component['cols'][key]['value']
                            component['cols'][key]['value'] = None
                            print(value)
                            k = value.split('.')
                            if len(k) == 2:
                                if k[0] in gv.data:
                                    if len(gv.data[k[0]]) > 0:
                                        if k[1] in gv.data[k[0]][0]:
                                            component['cols'][key]['value'] = gv.data[k[0]][0][k[1]]
                        if gv.comments_config and 'cols' in gv.comments_config and key in gv.comments_config['cols']:
                                # component['cols'][key] = gv.posts_config['cols'][key]
                                component['cols'][key] = gv.comments_config['cols'][key] | component['cols'][key]
    
                    elif component['id'] == 'form_categorie':
                        
                        if 'value' in component['cols'][key]:
                            value = component['cols'][key]['value']
                            component['cols'][key]['value'] = None
                            k = value.split('.')
                            if len(k) == 2:
                                if k[0] in gv.data:
                                    if len(gv.data[k[0]]) > 0:
                                        if k[1] in gv.data[k[0]][0]:
                                            component['cols'][key]['value'] = gv.data[k[0]][0][k[1]]
                       
                        if gv.categories_config and 'cols' in gv.categories_config and key in gv.categories_config['cols']:
                                component['cols'][key] = gv.categories_config['cols'][key] | component['cols'][key]
    
                    elif component['id'] == 'form_tag':
                        
                        if 'value' in component['cols'][key]:
                            value = component['cols'][key]['value']
                            component['cols'][key]['value'] = None
                            k = value.split('.')
                            if len(k) == 2:
                                if k[0] in gv.data:
                                    if len(gv.data[k[0]]) > 0:
                                        if k[1] in gv.data[k[0]][0]:
                                            component['cols'][key]['value'] = gv.data[k[0]][0][k[1]]
                       
                        if gv.tags_config and 'cols' in gv.tags_config and key in gv.tags_config['cols']:
                                component['cols'][key] = gv.tags_config['cols'][key] | component['cols'][key]
    
                    elif component['id'] == 'form_user':
                        
                        if 'value' in component['cols'][key]:
                            value = component['cols'][key]['value']
                            component['cols'][key]['value'] = None
                            k = value.split('.')
                            if len(k) == 2:
                                if k[0] in gv.data:
                                    if len(gv.data[k[0]]) > 0:
                                        if k[1] in gv.data[k[0]][0]:
                                            component['cols'][key]['value'] = gv.data[k[0]][0][k[1]]
                       
                        if gv.users_config and 'cols' in gv.users_config and key in gv.users_config['cols']:
                                component['cols'][key] = gv.users_config['cols'][key] | component['cols'][key]
                       
                    else:
                        if 'data_from' in component:
                            if component['data_from'] == 'comments':
                                
                                print('::::::::::::::::::::::::::::::::::::::::::::::::::::')
                                print(gv.comments_config)
                                print('::::::::::::::::::::::::::::::::::::::::::::::::::::')
                                
                                if  gv.comments_config and 'cols' in gv.comments_config and key in gv.comments_config['cols']:
                                    # component['cols'][key] = gv.comments_config['cols'][key]
                                    component['cols'][key] = gv.comments_config['cols'][key] | component['cols'][key]
                        else:
                            if  gv.posts_config and 'cols' in gv.posts_config and key in gv.posts_config['cols']:
                                # component['cols'][key] = gv.posts_config['cols'][key]
                                component['cols'][key] = gv.posts_config['cols'][key] | component['cols'][key]
                    
            template = Template(gv.HTML_TEMPLATES.get(component['type'], ''))
            
            rendered_children = {}
    
            if 'children' in component:
                if isinstance(component['children'], list):
                    rendered_children = []
                    for child in component.get('children', []):
                        child = PageRenderer.resolve_component(child)
                        #if 'data_from' in child and child['data_from'] in component.get('data', {}):
                        if False:
                            child['data'] = component.get('data', {})[child['data_from']]
                        
                        child['data'] = []
                        if 'data_from' in child:
                            if child['data_from'] in gv.data:
                                child['data'] = gv.data.get(child['data_from'], [])
    
                        else:
                            child['data'] = component.get('data', {})
                            
                        rendered_children.append(PageRenderer.generate_html(child))
                else:
                    for key, value in component['children'].items():
                        if isinstance(key, str): 
                            rendered_children[key] = [PageRenderer.generate_html(PageRenderer.resolve_component(child)) for child in value]
    
            h = template.render(
                attributes=component.get('attributes', {}),
                config=component.get('config', {}),
                data=component.get('data', {}),
                value=component.get('value', []),
                key=component.get('key', []),
                content=component.get('content', ''),
                files=component.get('files', []),
                items=component.get('items', []),
                cols=component.get('cols', {}),
                children=rendered_children,
                icons=gv.icons,
                classes=gv.classes,
                min=min,
                site_name='7777',
                format_attr=PageRenderer.format_attr,
                format_children=PageRenderer.format_children,
                breadcrumb_filter=PageRenderer.breadcrumb_filter
            )
    
            return h
        except Exception as e:
            print(e)
            return None
            
    @staticmethod
    def format_attr(attributes):
      s = ''
      if attributes:
        for attr, value in attributes.items():
            #if attr not in ['class']:
            
            if isinstance(value, str):
                #matches = re.findall(r'\{\{(.*?)\}\}', value)
                matches = re.findall(r'\{\{.*?\}\}', value)
    
                # 去除多余的空格
                matches = [match.strip() for match in matches]
    
                if matches:
                    param_name = matches[0]
                    
                    k = param_name.replace('{{','').replace('}}','').strip().split('.')
                    if len(k) == 2:
                        if k[0] in gv.data:
                            if len(gv.data[k[0]]) > 0:
                                if k[1] in gv.data[k[0]][0]:
    
                                    value = value.replace(param_name, str(gv.data[k[0]][0][k[1]]))
    
            s+=f' {attr}="{value}" '
      return s
    
    @staticmethod
    def format_children(children):
      s = ''
      if children:
        for child in children:
          # print((child)
          s += child
      return s
    
    @staticmethod
    def breadcrumb_filter(path: str) -> str:
        """
        Converts a path like '/Home/Documents/Add' into breadcrumb HTML.
        """
        parts = path.strip('/').split('/')
        return ''.join(f'<li><a href="/{part}">{part}</a></li>' for part in parts)

class CustomRenderer(PageRenderer):
    """继承 PageRenderer 并扩展功能"""

    def __init__(self, template_directory="templates"):
        super().__init__()
        self.templates_env = Environment(loader=FileSystemLoader(template_directory))
        self.templates_env.globals['min'] = min  # 可以添加自定义全局函数
        self.templates_env.globals['site_name'] = 'My Custom Site'

    @staticmethod
    async def get(request: Request):

        ConfigManager.load_data()
        
        gv.request = request
        
        full_path = request.url.path

        path_parts = full_path.strip("/").split("/")  # 分解路径为列表
        
        page_name = path_parts[-1]

        if page_name == '':
            page_name = 'main'
        
        page_config = PageRenderer.load_page_config(page_name + '_config.yaml')
    
        rendered_components = [PageRenderer.generate_html(component) for component in page_config['components']]
    
        template = Template(gv.BASE_HTML)
        h = template.render(
            page_title=page_config['title'],
            components=rendered_components,
            min=min
        )
    
        return h

    '''   
    # 主渲染函数保持不变
    # @app.get("/", response_class=HTMLResponse)
    # async def home(request: Request, current_user: dict = Depends(get_current_user)):
    #     logger.debug(f"Home page requested. Current user: {current_user}")
        
    #     if not current_user:
    #         logger.info("Unauthenticated user redirected to login")
    #         return RedirectResponse(url="/login", status_code=302)
    @staticmethod
    async def home(request: Request):
        
        gv.request = request
        
        full_path = request.url.path

        path_parts = full_path.strip("/").split("/")  # 分解路径为列表
        print(path_parts)
        
        ConfigManager.load_data()
    
        page_config = load_page_config()
        rendered_components = [PageRenderer.generate_html(component) for component in page_config['components']]
    
        template = Template(gv.BASE_HTML)
        return template.render(
            page_title=page_config['title'],
            components=rendered_components,
            min=min
        )
    '''
    
    # 主渲染函数保持不变
    # @app.get("/blog", response_class=HTMLResponse)
    @staticmethod
    async def get_blog(request: Request):
        
        gv.request = request
    
        query_params = dict(request.query_params)
        if query_params is None:
          query_params = []
    
        if 'api' in query_params:
            if 'posts' == query_params['api']:
              return await CustomRenderer.get_posts(request)
            elif 'post' == query_params['api']:
              return await CustomRenderer.get_post(request)
            elif 'edit' == query_params['api']:
              return await CustomRenderer.get_post_form(request)
        
        ConfigManager.load_data()
    
        posts_config = ConfigManager.get_table_config('posts')
        gv.posts_config = posts_config
          
        page_config = PageRenderer.load_page_config('blog_config.yaml')
        
        comments_config = ConfigManager.get_table_config('comments')
        gv.comments_config = comments_config
        
        categories_config = ConfigManager.get_table_config('categories')
        gv.categories_config = categories_config
        
        tags_config = ConfigManager.get_table_config('tags')
        gv.tags_config = tags_config
    
        users_config = ConfigManager.get_table_config('users')
        gv.users_config = users_config
       
        hx_get = '/blog' + '/posts'
        hx_get_params = []
        
        hx_get_params.append('api=posts')
        
        if 'search_term' in query_params:
            hx_get_params.append('search_term' + '=' + str(query_params['search_term']))
        if 'page_size' in query_params:
            hx_get_params.append('page_size' + '=' + str(query_params['page_size']))
        if 'page_number' in query_params:
            hx_get_params.append('page_number' + '=' + str(query_params['page_number']))
    
        hx_get_params.append('posts')
        
        hx_get += '?' + ('&').join(hx_get_params)
        
        blogs_attr = {
            'hx-get': '/api' + hx_get,
            'hx-swap': 'innerHTML',
            'hx-trigger': 'load, newPost from:body, updatePost from:body, deletePost from:body',
            'hx-url': hx_get
        }
        gv.component_dict['blogs']['attributes'] = gv.component_dict['blogs']['attributes'] | blogs_attr
    
        rendered_components = [PageRenderer.generate_html(component) for component in page_config['components']]
    
        template = Template(gv.BASE_HTML)
        h = template.render(
            page_title=page_config['title'],
            components=rendered_components,
            min=min
        )
    
        return h

    '''
    @staticmethod
    async def get_settings(request: Request):
        
        gv.request = request
        
        page_config = load_page_config('settings_config.yaml')
    
        rendered_components = [PageRenderer.generate_html(component) for component in page_config['components']]
    
        template = Template(gv.BASE_HTML)
        h = template.render(
            page_title=page_config['title'],
            components=rendered_components,
            min=min
        )
    
        return h
    
    @staticmethod
    async def get_about(request: Request):
        
        gv.request = request
        
        page_config = load_page_config('about_config.yaml')
    
        rendered_components = [PageRenderer.generate_html(component) for component in page_config['components']]
    
        template = Template(gv.BASE_HTML)
        h = template.render(
            page_title=page_config['title'],
            components=rendered_components,
            min=min
        )
    
        return h
        
    '''
    
    # @app.get("/blog/posts", response_class=HTMLResponse)
    # async def get_posts(request: Request):
    @staticmethod
    async def get_posts(request: Request):
        print('get_posts')
        print(request.url)
        path_parts = request.url.path.strip("/").split("/")  # 分解路径为列表
        print(path_parts)
     
        if "HX-Request" in request.headers:
            ## print((request.headers)
            pass
          
        query_params = dict(request.query_params)
    
        search_term = str(query_params['search_term']) if 'search_term' in query_params else ''
        page_size = int(query_params['page_size']) if 'page_size' in query_params else 5
        page_number = int(query_params['page_number']) if 'page_number' in query_params else 1
        post_id = int(query_params['post_id']) if 'post_id' in query_params else None
    
        result = TM.execute_transactions(
                    transaction_name = 'get_posts_list',
                    params={
                        'search_term': '%' + search_term + '%',
                        'limit': page_size,
                        'offset': (page_number - 1) * page_size,
                        'post_id': post_id
                    },
                    config_file="cms.yaml"
                )
     
        result = gv.data['posts']
        
        no_next = False
        if len(result) < page_size:
            no_next = True
        
        no_prev = False
        if page_number <= 1:
            no_prev = True
    
        h = ''
        try:
            PageRenderer.load_page_config('blog_config.yaml')
    
            for d in result:
              d['attributes'] = {
                'del': {
                  'hx-delete': f"/{path_parts[1]}/{path_parts[2]}?post_id={d['id']}&post" 
                },
                'edit': {
                  'hx-post': f"/{path_parts[1]}/{path_parts[2]}/form?post_id={d['id']}&post",
                  'hx-target': '#form_container'
                },
                'go': {
                  'hx-get': f"/api/{path_parts[1]}/{path_parts[2]}?post_id={d['id']}&post",
                  'hx-target': '#blogs'
                },
                'back': {
                    'hx-get': f'/api/{path_parts[1]}/{path_parts[2]}?api=posts',
                },
                'is_single': True if post_id is not None else False
              }
              
            gv.component_dict['posts']['data'] = gv.data #result
    
            hx_url = f"/{path_parts[1]}/{path_parts[2]}?search_term={search_term}&page_size={page_size}&page_number={page_number - 1}"
            hx_get = '/api' + hx_url + '&api=posts'
    
            prev_attr = {
                        'id': 'prev',
                        'hx-get': hx_get, 
                        'hx-swap': 'innerHTML',
                        'hx-target': '#blogs',
                        'hx-url': hx_url,
                    }
            if no_prev:
                prev_attr['disabled'] = True
    
            hx_url = f"/{path_parts[1]}/{path_parts[2]}?search_term={search_term}&page_size={page_size}&page_number={page_number + 1}"
            hx_get = '/api' + hx_url + '&api=posts'
    
            next_attr = {
                        'id': 'prev',
                        'hx-get': hx_get, 
                        'hx-swap': 'innerHTML',
                        'hx-target': '#blogs',
                        'hx-url': hx_url,
                    }
            if no_next:
                next_attr['disabled'] = True
    
            gv.component_dict['posts']['config'] = {
                'prev': {
                    'attributes': prev_attr
                },
                'next': {
                    'attributes': next_attr
                },
                'is_single': True if post_id is not None else False
            }
            h = PageRenderer.generate_html(gv.component_dict['posts'])
        except Exception as e:
            pass
    
        return HTMLResponse(content=h)
        
    @staticmethod
    @app.get("/blog/post", response_class=HTMLResponse)
    async def get_post(request: Request):
        
        if "HX-Request" in request.headers:
            pass
            parsed_url = urlparse(request.headers['hx-current-url'])
    
        query_params = dict(request.query_params)
    
        if 'post_id' not in query_params:
          return 'no data'
    
        post_id = int(query_params['post_id'])
    
        result = TM.execute_transactions(
                    transaction_name = 'get_post_detail',
                    params={
                        'post_id': post_id
                    },
                    config_file="cms.yaml"
                )
        result = [dict(row) for row in result]  # 转换为字典列表
    
        for d in result:
            d['attributes'] = {
                'back': {
                    'hx-get': f'/api{parsed_url.path}?{parsed_url.query}&api=posts',
                }
            }
    
        h = ''
        try:
            PageRenderer.load_page_config('blog_config.yaml')
            gv.component_dict['post']['data'] = result
    
            h = PageRenderer.generate_html(gv.component_dict['post'])
        except Exception as e:
            pass
    
        return HTMLResponse(content=h)
        

    @staticmethod
    @app.post("/blog/post/form", response_class=HTMLResponse)
    async def get_post_form(request: Request):
        if "HX-Request" in request.headers:
            pass
    
        parsed_url = urlparse(request.headers['hx-current-url'])
        
        query_params = dict(request.query_params)
         
        result = []
        
        if 'post_id' in query_params:
          
          post_id = int(query_params['post_id'])
       
          result = TM.execute_transactions(
                      transaction_name = 'get_post_detail',
                      params={
                          'post_id': post_id
                      },
                      config_file="cms.yaml"
                  )
          result = [dict(row) for row in result]  # 转换为字典列表
          
          h = ''
          try:
              if len(result) > 0:
                  PageRenderer.load_page_config('blog_config.yaml')
                  gv.component_dict['form_edit']['data'] = result[0]
                  
                  h = PageRenderer.generate_html(gv.component_dict['form_edit'])
          except Exception as e:
              pass
      
          return HTMLResponse(content=h)
          
        else:
          
          h = ''
          try:
              if True:
                  PageRenderer.load_page_config('blog_config.yaml')
                  gv.component_dict['form_edit']['data'] = result
                  
                  h = generate_html(gv.component_dict['form_create'])
          except Exception as e:
              pass
      
          return HTMLResponse(content=h)

class DatabaseManager:
    """数据库管理类，处理数据库连接和操作"""
    DATABASE_URL = "sqlite:///./cms.db"
    engine = create_engine(DATABASE_URL)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    metadata = MetaData()
    metadata.reflect(bind=engine, views=True)

    db = SessionLocal()
    transaction_manager = TransactionModule(engine=engine, db=db, metadata=metadata)

    '''
    @staticmethod
    def get_table_names(self):
        inspector = inspect(self.engine)
        return inspector.get_table_names()
    '''
    
    @staticmethod
    def get_table_names():
        inspector = inspect(engine)
        return inspector.get_table_names()
    
    @staticmethod
    def get_view_names():
        inspector = inspect(engine)
        return inspector.get_view_names()

    @staticmethod
    def get_tables():
        tables = DatabaseManager.get_table_names()
        views = DatabaseManager.get_view_names()
        values = []
        for t in tables:
            values.append(
                {
                    'component_id': 'main_data_table',
                    'text': t
                }
            )
            gv.models.append(t)
            gv.model[t] = {
                'is_view': False
            }
        for v in views:
            values.append(
                {
                    'component_id': 'main_data_table',
                    'text': v
                }
            )
            gv.models.append(v)
            gv.model[v] = {
                'is_view': True
            }
        return values
    

    @staticmethod
    def generate_table_or_view_config(engine, name, is_view=False):
        inspector = inspect(engine)
        columns = inspector.get_columns(name)
        
        config_path = f'table_configs/{name}_config.yaml'
        
        # Check if configuration file exists
        if os.path.exists(config_path):
            # Read existing configuration file
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)
                return config
            
        config = {
            "name": name,
            "type": "view" if is_view else "table",
            "columns": []
        }
    
        for column in columns:
            column_config = {
                "name": column['name'],
                "label": column['name'],
                "type": str(column['type']),
                "nullable": column.get('nullable', True),  # Views might not have this information
                "primary_key": column.get('primary_key', False)  # Views might not have this information
            }
    
            # Check if the column is auto-increment
            if column.get('autoincrement', False):
                column_config['autoincrement'] = True
    
            if column.get('primary_key', False) and isinstance(column['type'], Integer):
                # Additional checks might be needed depending on the database
                column_config['autoincrement'] = True
    
            # Determine input type and additional properties
            if isinstance(column['type'], String):
                column_config['input_type'] = 'text'
            elif isinstance(column['type'], (Integer, Float)):
                column_config['input_type'] = 'number'
            elif isinstance(column['type'], (DateTime, Date)):
                column_config['input_type'] = 'date'
            elif isinstance(column['type'], Boolean):
                column_config['input_type'] = 'checkbox'
            elif isinstance(column['type'], Enum):
                column_config['input_type'] = 'select'
                column_config['options'] = column['type'].enums
            else:
                column_config['input_type'] = 'text'
    
            config['columns'].append(column_config)
    
        # Save configuration to a YAML file
        os.makedirs('table_configs', exist_ok=True)
        with open(config_path, 'w') as f:
            yaml.dump(config, f, default_flow_style=False)
    
        return config
    
    # Generate configurations for all tables and views
    @staticmethod
    def generate_all_configs(engine):
        inspector = inspect(engine)
        
        # Generate config for tables
        for table_name in inspector.get_table_names():
            DatabaseManager.generate_table_or_view_config(engine, table_name)
        
        # Generate config for views
        for view_name in inspector.get_view_names():
            DatabaseManager.generate_table_or_view_config(engine, view_name, is_view=True)
    
    @staticmethod
    def apply_search_filter(query, table, column_config, value, is_keyword_search=False):
        """
        Apply search filter to a query based on column configuration and search value.
        根据列配置和搜索值对查询应用搜索过滤器。
        
        Args:
            query: SQLAlchemy query object
                  SQLAlchemy查询对象
            table: SQLAlchemy table object
                   SQLAlchemy表对象
            column_config: Dictionary containing column configuration
                          包含列配置的字典
            value: Search value
                   搜索值
            is_keyword_search: Boolean indicating if this is a keyword search across all columns
                              布尔值，指示是否是跨所有列的关键字搜索
        
        Returns:
            Modified query with search filter applied
            应用了搜索过滤器的修改后的查询
        """
        if value:
            column = getattr(table.c, column_config['name'])
            input_type = column_config.get('input_type', 'text')
            
            # For keyword search, we only apply LIKE filters on text and string columns
            # 对于关键字搜索，我们只对文本和字符串列应用LIKE过滤器
            if is_keyword_search:
                if isinstance(column.type, String):
                    return query.where(column.ilike(f"%{value}%"))
                return query
                
            if input_type == 'text':
                return query.where(column.ilike(f"%{value}%"))
            elif input_type == 'number':
                try:
                    value = float(value)
                    return query.where(column == value)
                except ValueError:
                    return query
            elif input_type in ('date', 'datetime'):
                try:
                    value = datetime.strptime(value, "%Y-%m-%d")
                    return query.where(column == value)
                except ValueError:
                    return query
            elif input_type == 'checkbox':
                value = value.lower() in ('true', '1', 'yes', 'on')
                return query.where(column == value)
            elif input_type == 'select':
                return query.where(column == value)
        return query

    @staticmethod
    def get_table_data(
        request: Request = None, 
        table_name: str = None, 
        page: int = 1, 
        page_size: int = 5, 
        sort_column: str | None = None, 
        sort_direction: str = 'asc'
    ):
    
        if request is None:
            request = gv.request
        
        search_params = {}
        if request:
            # Get query parameters from request
            # 从请求中获取查询参数
            search_params = dict(request.query_params)
            
            # Process pagination parameters
            # 处理分页参数
            if 'page' in search_params:
                if search_params['page'] == '':
                    page = 1
                else:
                    page = int(search_params['page'])
    
            if 'page_size' in search_params:
                if search_params['page_size'] == '':
                    page_size = 10
                else:
                    page_size = int(search_params['page_size'])
            
            # Process sorting parameters
            # 处理排序参数
            if 'sort_column' in search_params:
                sort_column = search_params['sort_column']
    
            if 'sort_direction' in search_params:
                sort_direction = search_params['sort_direction']
    
            if 'table_name' in search_params:
                table_name = search_params['table_name']
    
            # Remove known parameters from search params
            # 从搜索参数中移除已知参数
            for param in ['page', 'page_size', 'sort_column', 'sort_direction']:
                search_params.pop(param, None)
    
        # Set default table if none specified
        # 如果未指定表，设置默认表
        if table_name is None:
            table_name = 'users'
    
        # Get table object and verify it exists
        # 获取表对象并验证其存在
        table = None
        if table_name in metadata.tables:
            table = metadata.tables[table_name]
        if table is None:
            raise HTTPException(status_code=404, detail="Table not found")
    
        table_config = ConfigManager.get_table_config(table_name)
        
        # Get primary key and calculate offset for pagination
        # 获取主键并计算分页的偏移量
        primary_key = next((col['name'] for col in table_config['columns'] if col.get('primary_key')), None)
        offset = (page - 1) * page_size
        
        query = select(table.columns)
        
        # Handle keyword search across all columns
        # 处理跨所有列的关键字搜索
        if 'keyword' in search_params and search_params['keyword']:
            keyword = search_params['keyword']
            keyword_conditions = []
            for column_config in table_config['columns']:
                column = getattr(table.c, column_config['name'])
                # Only apply keyword search to text/string columns
                # 只对文本/字符串列应用关键字搜索
                if isinstance(column.type, String):
                    keyword_conditions.append(column.ilike(f"%{keyword}%"))
            if keyword_conditions:
                query = query.where(or_(*keyword_conditions))
        else:
            # Apply regular column-specific filters
            # 应用常规的列特定过滤器
            for column_config in table_config['columns']:
                if column_config['name'] in search_params:
                    query = DatabaseManager.apply_search_filter(query, table, column_config, search_params[column_config['name']])
        
        # Apply sorting if a sort column is specified
        # 如果指定了排序列，应用排序
        if sort_column and sort_column in table.columns:
            sort_func = desc if sort_direction.lower() == 'desc' else asc
            query = query.order_by(sort_func(getattr(table.c, sort_column)))
        
        with SessionLocal() as session:
            # Get total count and paginated results
            # 获取总数和分页结果
            count_query = select(func.count()).select_from(query.alias())
            total_items = session.execute(count_query).scalar()
            result = session.execute(query.offset(offset).limit(page_size)).fetchall()
            
        # Calculate total pages
        # 计算总页数
        total_pages = (total_items + page_size - 1) // page_size
        
        # Return the complete result set
        # 返回完整的结果集
        return {
              "request": request,
              "table_name": table_name,
              "columns": [col['name'] for col in table_config['columns']],
              "rows": result,
              "primary_key": primary_key,
              "page": page,
              "page_size": page_size,
              "total_items": total_items,
              "total_pages": total_pages,
              "table_config": table_config,
              "sort_column": sort_column,
              "sort_direction": sort_direction,
              "search_params": search_params
          }
        
        
class AuthManager:
    """用户认证管理类"""
    
    @staticmethod
    def verify_password(plain_password, hashed_password):
        return ConfigManager.pwd_context.verify(plain_password, hashed_password)

    @staticmethod
    def get_password_hash(password):
        return ConfigManager.pwd_context.hash(password)

    @staticmethod
    def create_access_token(data: dict, expires_delta: timedelta = None):
        to_encode = data.copy()
        expire = datetime.utcnow() + (expires_delta or timedelta(minutes=15))
        to_encode.update({"exp": expire})
        return jwt.encode(to_encode, ConfigManager.SECRET_KEY, algorithm=ConfigManager.ALGORITHM)

    @staticmethod
    async def get_current_user(request: Request):
        token = request.cookies.get("access_token")
        if not token:
            return None
        try:
            payload = jwt.decode(token, ConfigManager.SECRET_KEY, algorithms=[ConfigManager.ALGORITHM])
            username: str = payload.get("sub")
            if username is None:
                raise HTTPException(status_code=401, detail="Invalid token")
            return {"username": username}
        except JWTError:
            return none
    
    def verify_password(plain_password, hashed_password):
        return pwd_context.verify(plain_password, hashed_password)
    
    def get_password_hash(password):
        return pwd_context.hash(password)
    
    def create_access_token(data: dict, expires_delta: timedelta = None):
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=15)
        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
        return encoded_jwt
    
    #async def get_current_user(request: Request, token: Optional[str] = Depends(oauth2_scheme)):
    async def get_current_user(request: Request):
    
        token = request.cookies.get("access_token")
        
        if not token:
            return None
            
        credentials_exception = HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            username: str = payload.get("sub")
            if username is None:
                raise credentials_exception
        #except JWTError:
        #    raise credentials_exception
        except JWTError:
            # 检查请求头，判断是否是 HTMX 请求
            if "HX-Request" in request.headers:
                # 如果是 HTMX 请求，返回 401 错误
                raise credentials_exception
            else:
                # 如果不是 HTMX 请求，重定向到登录页面
                return RedirectResponse(url=f"/login?next={request.url.path}", status_code=302)
    
        # db = SessionLocal()
        try:
            user = db.execute(select(metadata.tables['Users']).where(
                metadata.tables['Users'].c.Username == username
            )).first()
            if user is None:
                raise credentials_exception
            return user
        finally:
            db.close()
    
    def decode_token(token: str):
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            username: str = payload.get("sub")
            if username is None:
                raise HTTPException(status_code=401, detail="Invalid token")
            return {"username": username, "role": payload.get("role")}
        except JWTError:
            raise HTTPException(status_code=401, detail="Invalid token")
    
    def login_required(func):
        @wraps(func)
        async def wrapper(request: Request, *args, **kwargs):
            token = None
            
            # 首先检查 Authorization header
            auth_header = request.headers.get('Authorization')
            if auth_header and auth_header.startswith('Bearer '):
                token = auth_header.split()[1]
            
            # 如果 header 中没有 token，则检查 cookie
            if not token:
                token = request.cookies.get('access_token')
            
            if not token:
                raise HTTPException(status_code=401, detail="Not authenticated")
            
            try:
                user = decode_token(token)
                # 将用户信息添加到请求中，以便在路由函数中使用
                request.state.user = user
            except HTTPException:
                raise HTTPException(status_code=401, detail="Invalid token")
            
            return await func(request, *args, **kwargs)
        return wrapper
    
    
    @app.get("/login", response_class=HTMLResponse)
    # async def login(request: Request, current_user: dict = Depends(get_current_user)):
    #     """
    #     Handle GET requests to the login page
    #     处理登录页面的GET请求
        
    #     Args:
    #         request: FastAPI request object
    #         current_user: Current user from JWT token dependency
    #     """
    #     # If user is already logged in, redirect to home page
    #     # 如果用户已经登录，重定向到主页
    #     if current_user:
    #         return RedirectResponse(url="/", status_code=302)
    async def login(request: Request):
    
        gv.request = request
        
        # Load latest configuration
        # 加载最新配置
        ConfigManager.load_data()
    
        # Load login page configuration
        # 加载登录页面配置
        page_config = PageRenderer.load_page_config('login_config.yaml')
        
        # Render login page components
        # 渲染登录页面组件
        rendered_components = [generate_html(component) for component in page_config['components']]
        
        template = Template(gv.BASE_HTML)
        return template.render(
            page_title="User Management",
            components=rendered_components,
            min=min
        )
        
    @app.post("/login")
    async def login(request: Request, response: Response):
        """
        Handle POST requests for login
        处理登录的POST请求
        """
        form_data = await request.form()
        params = {key: value for key, value in form_data.items()}
        
        try:
            # with SessionLocal() as db:
            result = TM.execute_transactions(
                transaction_name = "UserLogin", 
                params = params,
                config_file = "login_txn.yaml"
            )
                
            user_data = gv.data.get("user_data", [])
    
            if not user_data or not verify_password(params['password'], user_data[0]["Password"]):
                return "<div class='alert alert-error'>Incorrect username or password</div>"
            
            user = user_data[0]
            access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
            access_token = create_access_token(
                data={"sub": user["Username"], "role": user["Role"]},
                expires_delta=access_token_expires
            )
            
            html_response = f"<div class='alert alert-success'>Login successful! Welcome</div>"
            response = HTMLResponse(content=html_response)
            
            # Set secure cookie with token
            # 设置带有令牌的安全cookie
            response.set_cookie(
                key="access_token",
                value=access_token,
                httponly=True,
                secure=True,  # Only transmit over HTTPS
                samesite='lax',  # Prevent CSRF
                max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60
            )
            
            # Set cache control headers to prevent caching of login page
            # 设置缓存控制头以防止登录页面被缓存
            response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, post-check=0, pre-check=0'
            response.headers['Pragma'] = 'no-cache'
            response.headers['Expires'] = '0'
            response.headers['HX-Redirect'] = '/'
            
            return response
            
        except Exception as e:
            return HTMLResponse(content=f"<div class='alert alert-error'>Login failed: {str(e)}</div>")
    
    @app.middleware("http")
    async def cache_control_middleware(request: Request, call_next):
        """
        Middleware to handle cache control headers
        处理缓存控制头的中间件
        """
        response = await call_next(request)
        
        # Add cache control headers for login-related pages
        # 为登录相关页面添加缓存控制头
        if request.url.path in ["/login", "/register"]:
            response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, post-check=0, pre-check=0'
            response.headers['Pragma'] = 'no-cache'
            response.headers['Expires'] = '0'
        
        return response
        
    @app.get("/logout")
    async def logout(request: Request):
        logger.info("Logout requested")
        #response = RedirectResponse(url="/login", status_code=302)
        response = HTMLResponse(content='')
        response.headers['HX-Redirect'] = '/login'
        response.delete_cookie(key="access_token")
        logger.info("access_token cookie deleted")
        return response
        
    @app.get("/register", response_class=HTMLResponse)
    async def register(request: Request):
        gv.request = request
        
        ConfigManager.load_data()  # 重新加载配置，确保使用最新的配置
    
        page_config = PageRenderer.load_page_config('register_config.yaml')
        
        rendered_components = [generate_html(component) for component in page_config['components']]
    
        template = Template(gv.BASE_HTML)
        return template.render(
            page_title="User Management",
            components=rendered_components,
            min=min
        )
    
    @app.post("/register", response_class=HTMLResponse)
    async def register(request: Request):
        form_data = await request.form()
        params = {key: value for key, value in form_data.items()}
        params['password'] = get_password_hash(params['password'])
        try:
            with SessionLocal() as db:
                result = TM.execute_transactions(
                    transaction_name = "RegisterUser", 
                    params = params,
                    config_file="register_txn.yaml"
                )
            #return f"<div class='alert alert-success'>User registered successfully!</div>"
            response = HTMLResponse(content='')
            response.headers['HX-Redirect'] = '/login'
            response.delete_cookie(key="access_token")
            logger.info("access_token cookie deleted")
            return response
        except Exception as e:
            return f"<div class='alert alert-error'>Registration failed: {str(e)}</div>"

class FileManager:
    """文件管理类，处理上传、验证"""
    ALLOWED_EXTENSIONS = {'.txt', '.pdf', '.png', '.jpg', '.jpeg', '.gif'}
    MAX_FILE_SIZE = 5 * 1024 * 1024  # 5 MB

    @staticmethod
    def allowed_file(filename: str) -> bool:
        return os.path.splitext(filename)[1].lower() in FileManager.ALLOWED_EXTENSIONS

    @staticmethod
    async def upload_file(file: UploadFile = File(...)):
        if not FileManager.allowed_file(file.filename):
            return HTMLResponse(f"<div class='error'>Unsupported file type</div>")

        file_path = f"./uploaded/{file.filename}"
        with open(file_path, "wb") as buffer:
            buffer.write(file.file.read())

        return HTMLResponse(f"<div class='success'>File uploaded successfully</div>")

    def validate_file_type(file: UploadFile) -> bool:
        mime = magic.Magic(mime=True)
        file_type = mime.from_buffer(file.file.read(1024))
        file.file.seek(0)  # Reset file pointer
        return file_type.split('/')[1] in [ext.lstrip('.') for ext in ALLOWED_EXTENSIONS]
    
    def validate_file_size(file: UploadFile) -> bool:
        file.file.seek(0, 2)  # Move to the end of the file
        file_size = file.file.tell()  # Get the position (size)
        file.file.seek(0)  # Reset file pointer
        return file_size <= MAX_FILE_SIZE
        
    #@app.post("/upload", response_class=HTMLResponse)
    def upload_file(
            file: UploadFile = File(...)
        ):
        try:
            # 文件验证
            if not allowed_file(file.filename):
                return HTMLResponse(f"<div class='error'>File type not allowed. Allowed types are: {', '.join(ALLOWED_EXTENSIONS)}</div>")
            
            # if not validate_file_type(file):
            #     return HTMLResponse("<div class='error'>File content does not match the allowed types</div>")
            
            if not validate_file_size(file):
                return HTMLResponse(f"<div class='error'>File size exceeds the maximum limit of {MAX_FILE_SIZE / (1024 * 1024)} MB</div>")
            
            # # 临时保存文件
            # temp_file_path = f"./temp_uploads/{file.filename}"
            # os.makedirs(os.path.dirname(temp_file_path), exist_ok=True)
            # with open(temp_file_path, "wb") as buffer:
            #     shutil.copyfileobj(file.file, buffer)
            
            # 准备事务参数
            transaction_params = {
                "file": file,
                "file_name": file.filename,
                "folder_path": "./uploaded"
            }
            
            # 执行事务
            try:
                result = TM.execute_transactions(
                    transaction_name='file_operations',
                    params=transaction_params,
                    config_file='file_operations_txn.yaml'
                )
    
                # # 删除临时文件
                # os.remove(temp_file_path)
                
                # 根据结果返回适当的响应
                if isinstance(result, dict) and 'filename' in result:
                    PageRenderer.load_page_config()
                    # # # print((gv.component_dict.keys())
                    res = PageRenderer.generate_html(gv.component_dict['file_manager'])
                    res = f'''
                    <div hx-swap-oob="innerHTML:#file-manager">
                        {res}
                    </div>
                    '''
                    return HTMLResponse(res)
                    # return HTMLResponse(f"<div class='success'>File '{result['filename']}' processed successfully</div>")
                else:
                    return HTMLResponse(f"<div class='success'>Transaction completed successfully</div>")
            
            except HTTPException as he:
                return HTMLResponse(f"<div class='error'>{he.detail}</div>")
            
            except Exception as e:
                logger.error(f"Error during transaction execution: {str(e)}")
                return HTMLResponse(f"<div class='error'>An error occurred during transaction execution: {str(e)}</div>")
        
        except Exception as e:
            logger.error(f"Error during file upload: {str(e)}")
            return HTMLResponse(f"<div class='error'>An error occurred during file upload: {str(e)}</div>")
    
    def get_files():
        files = os.listdir("uploaded")
        return files
    
    #@app.get("/preview/{filename}", response_class=HTMLResponse)
    async def preview_file(request: Request, filename: str):
        file_path = Path(f"uploaded/{filename}")
        if file_path.is_file():
            if file_path.suffix.lower() in ['.jpg', '.jpeg', '.png', '.gif']:
                res = f'''
                    <div>
                        <h2>Preview: { filename }</h2>
                        <img src="./uploaded/{ filename }" alt="{ filename }" style="max-width:100%;max-height:600px;">
                    </div>
                '''
                return res
        res = f'''
            <div>
                File not found or not supported
            </div>
        '''
        return res
        
if __name__ == "__main__":
  
    init()
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        workers=2,
        log_level="debug",
        access_log=False,
        reload_dirs=["./"]
    )



def generate_table_config(engine, table_name):
    inspector = inspect(engine)
    columns = inspector.get_columns(table_name)
    
    config_path = f'table_configs/{table_name}_config.yaml'
    
    # Check if configuration file exists
    if os.path.exists(config_path):
        # Read existing configuration file
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
            return config
        
    config = {
        "table_name": table_name,
        "columns": []
    }

    for column in columns:
        column_config = {
            "name": column['name'],
            "label": column['name'],
            "type": str(column['type']),
            "nullable": column['nullable'],
            "primary_key": column['primary_key']
        }

        # Determine input type and additional properties
        if isinstance(column['type'], String):
            column_config['input_type'] = 'text'
        elif isinstance(column['type'], (Integer, Float)):
            column_config['input_type'] = 'number'
        elif isinstance(column['type'], (DateTime, Date)):
            column_config['input_type'] = 'date'
        elif isinstance(column['type'], Boolean):
            column_config['input_type'] = 'checkbox'
        elif isinstance(column['type'], Enum):
            column_config['input_type'] = 'select'
            column_config['options'] = column['type'].enums
        else:
            column_config['input_type'] = 'text'

        config['columns'].append(column_config)

    # Save configuration to a YAML file
    with open(f'table_configs/{table_name}_config.yaml', 'w') as f:
        yaml.dump(config, f, default_flow_style=False)

    return config
    
'''


@app.get("/component", response_class=HTMLResponse)
# async def rendered_component(request: Request, current_user: dict = Depends(get_current_user)):
async def rendered_component(request: Request):
    gv.request = request
    query_params = dict(request.query_params)

    if "HX-Request" in request.headers:
        # 如果是 HTMX 请求，重新抛出异常
        pass
    else:
        # 如果是普通请求，重定向到登录页面
        return await home(request, current_user)
        pass
      
    if 'component_id' in query_params:
        component_id = query_params['component_id']
    elif 'table_name' in query_params:
            component_id = 'main_data_table'
    else:
        return ''

    PageRenderer.load_page_config()

    res = generate_html(gv.component_dict[component_id])
    return res

@app.get("/tables")
async def read_root(request: Request):
    tables = get_table_names()
    return templates.TemplateResponse("all_in_one.html", {"request": request, "tables": tables})

@app.get("/table/{table_name}")
async def read_table(request: Request, table_name: str):

    if table_name not in gv.models:
        raise HTTPException(status_code=404, detail="Table not found")
    
    table_config = ConfigManager.get_table_config(table_name)
    return templates.TemplateResponse("all_in_one.html", {
        "request": request,
        "table_name": table_name,
        "table_config": table_config
    })

@app.get("/table_content/{table_name}")
async def read_table_content(
        request: Request, 
        table_name: str, 
        page: int = 1, 
        page_size: int = 10,
        sort_column: str | None = None,
        sort_direction: str = 'asc'
    ):

    # if table_name not in metadata.tables:
    #     raise HTTPException(status_code=404, detail="Table not found")
    table = None
    if table_name in metadata.tables:
        table = metadata.tables[table_name]
    if table is None:
        raise HTTPException(status_code=404, detail="Table not found")

    table_config = ConfigManager.get_table_config(table_name)
    # table = metadata.tables[table_name]
    primary_key = next(col['name'] for col in table_config['columns'] if col.get('primary_key', False))
    offset = (page - 1) * page_size
    
    query = select(table.columns)
    
    # Get all query parameters
    search_params = dict(request.query_params)
    # Remove known parameters
    for param in ['page', 'page_size', 'sort_column', 'sort_direction']:
        search_params.pop(param, None)
    
    # Apply search filters for each column based on JSON configuration
    for column_config in table_config['columns']:
        if column_config['name'] in search_params:
            query = DatabaseManager.apply_search_filter(query, table, column_config, search_params[column_config['name']])
    
    # Apply sorting if a sort column is specified
    if sort_column and sort_column in table.columns:
        sort_func = desc if sort_direction.lower() == 'desc' else asc
        query = query.order_by(sort_func(getattr(table.c, sort_column)))
    
    with SessionLocal() as session:
        count_query = select(func.count()).select_from(query.alias())
        total_items = session.execute(count_query).scalar()
        result = session.execute(query.offset(offset).limit(page_size)).fetchall()
        
    total_pages = (total_items + page_size - 1) // page_size
    
    return templates.TemplateResponse("table_content.html", {
        "request": request,
        "table_name": table_name,
        "columns": [col['name'] for col in table_config['columns']],
        "rows": result,
        "primary_key": primary_key,
        "page": page,
        "page_size": page_size,
        "total_items": total_items,
        "total_pages": total_pages,
        "table_config": table_config,
        "sort_column": sort_column,
        "sort_direction": sort_direction,
        "search_params": search_params
    })
    

@app.get("/form_config/{table_name}")
async def get_form_config(table_name: str):
    if table_name not in metadata.tables:
        raise HTTPException(status_code=404, detail="Table not found")
    return generate_form_config(table_name)

@app.get("/record/{table_name}/{id}")
async def get_record(table_name: str, id: str):
    if table_name not in metadata.tables:
        raise HTTPException(status_code=404, detail="Table not found")
    
    table = metadata.tables[table_name]
    primary_key = ConfigManager.get_primary_key(table)
    
    with SessionLocal() as session:
        stmt = select(table).where(getattr(table.c, primary_key) == id)
        result = session.execute(stmt).fetchone()
        if result:
            return dict(result._mapping)
        else:
            raise HTTPException(status_code=404, detail="Record not found")

@app.get("/execute_all_transactions")
def execute_transactions():
    try:
        with SessionLocal() as db:
            return TM.execute_all_transactions(db)
    except HTTPException as e:
        logger.error(f"Error executing transactions: {e.detail}")
        logger.error(traceback.format_exc())
        raise
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")

@app.get("/test", response_class=HTMLResponse)
async def blog(request: Request):
    
    gv.request = request

    query_params = dict(request.query_params)
    
    ConfigManager.load_data()

    page_config = PageRenderer.load_page_config('test_config.yaml')

    rendered_components = [generate_html(component) for component in page_config['components']]

    template = Template(gv.BASE_HTML)
    h = template.render(
        page_title=page_config['title'],
        components=rendered_components,
        min=min
    )
    
    return h;
    

@app.get("/api/data", response_class=HTMLResponse)
async def api_data(request: Request):
    
    gv.request = request

    query_params = dict(request.query_params)
    ## print((query_params)

    return str(query_params);


def get_column_type(column_type):
    if isinstance(column_type, String):
        return "text"
    elif isinstance(column_type, Integer):
        return "number"
    elif isinstance(column_type, Boolean):
        return "checkbox"
    elif isinstance(column_type, (DateTime, Date)):
        return "date"
    else:
        return "text"  # 默认为文本输入

def generate_form_config(table_name):
    table = metadata.tables[table_name]
    inspector = inspect(engine)
    pk_constraint = inspector.get_pk_constraint(table_name)
    primary_keys = pk_constraint['constrained_columns'] if pk_constraint else []

    fields = []
    for column in table.columns:
        field = {
            "name": column.name,
            "label": column.name.replace('_', ' ').title(),
            "type": get_column_type(column.type),
            "required": not column.nullable and column.name not in primary_keys,
            "readonly": column.name in primary_keys
        }
        fields.append(field)

    return {"fields": fields}

    
    @staticmethod
    def get_configs():
        return ConfigManager.get_table_config()


'''

'''
# Set up the Jinja2 environment
env = Environment(loader=FileSystemLoader('.'))

# Define globals
env.globals['site_name'] = "My Awesome Site"
# env.globals['get_user'] = lambda user_id: fetch_user_from_db(user_id)  # A function
'''