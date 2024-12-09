import os
import uvicorn
import json

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

'''
# Set up the Jinja2 environment
env = Environment(loader=FileSystemLoader('.'))

# Define globals
env.globals['site_name'] = "My Awesome Site"
# env.globals['get_user'] = lambda user_id: fetch_user_from_db(user_id)  # A function
'''

from jose import JWTError, jwt
from datetime import datetime, timedelta
from functools import wraps

import pprint
import yaml
import logging
import copy
import transaction_module
import gv as gv

from pathlib import Path

from transaction_module import convert_value, TransactionModule

app = FastAPI()

from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 允许所有来源，您可以根据需要指定特定的源
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")

# app.mount("/files", StaticFiles(directory="files"), name="files")
app.mount("/uploaded", StaticFiles(directory="uploaded"), name="uploaded")

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

# JWT 相关设置
SECRET_KEY = "your-secret-key"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

gv.BASE_HTML = None
gv.HTML_TEMPLATES = None
gv.YAML_CONFIG = None

# 设置密码哈希
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# def get_db():
#     db = SessionLocal()
#     try:
#         yield db
#     finally:
#         db.close()

def load_data_from_html(filename: str) -> Optional[str]:
    try:
        with open(filename, "r", encoding="utf-8") as file:
            return file.read()
    except IOError as e:
        logging.error(f"Error loading data from {filename}: {e}")
        return None

def load_data_from_yaml(filename: str) -> Optional[Dict[str, Any]]:
    try:
        if filename is None:
            filename = 'main_config.yaml'
        with open(filename, "r", encoding="utf-8") as file:
            return yaml.safe_load(file)
    except (IOError, yaml.YAMLError) as e:
        logging.error(f"Error loading YAML data from {filename}: {e}")
        return None

def load_data():
    
    gv.BASE_HTML = load_data_from_html('base_html.html')
  
    gv.HTML_TEMPLATES = load_data_from_yaml('html_templates.yaml')
  
    gv.YAML_CONFIG = load_data_from_yaml('main_config.yaml')

    gv.icons = gv.HTML_TEMPLATES.get('icons', {})
    
    gv.classes = gv.HTML_TEMPLATES.get('classes', {})

def verify_password(plain_password, hashed_password):
    # print(plain_password)
    # print(hashed_password)
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    # print(password)
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

    # print('get_current_user')

    token = request.cookies.get("access_token")
    # print(token)
    
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
    # print('login_required')
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


def get_configs():
    return get_table_config()

gv.model = {}
gv.models = []

def get_tables():
    tables = get_table_names()
    views = get_view_names()
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

# 修改渲染函数
def generate_html(component: Dict[str, Any]) -> str:

    # print('::::::::::::::::::::::::::::::::::::::::::::::::::::')
    # print(component)
    # print('::::::::::::::::::::::::::::::::::::::::::::::::::::')

    for key in ['config', 'data', 'value', 'files']:
        if key in component and isinstance(component[key], str):
            if component[key] in globals():
                component[key] = globals()[component[key]]()
    
    if 'cols' in component:
        for key in component['cols']:
            if  gv.posts_config and 'cols' in gv.posts_config and key in gv.posts_config['cols']:
                # component['cols'][key] = gv.posts_config['cols'][key]
                component['cols'][key] = gv.posts_config['cols'][key] | component['cols'][key]
        
        #print('::::::::::::::::::::::::::::::::::::::::::::::::::::')
        #print(component['cols'])
        #print('::::::::::::::::::::::::::::::::::::::::::::::::::::')

    template = Template(gv.HTML_TEMPLATES.get(component['type'], ''))

    rendered_children = {}

    if 'children' in component:
      if isinstance(component['children'], list):
        # print("这是一个数组（列表）")
        #rendered_children = [generate_html(resolve_component(child)) for child in component.get('children', [])]
        
        rendered_children = []
        for child in component.get('children', []):
            child = resolve_component(child)
            child['data'] = component.get('data', {})
            rendered_children.append(generate_html(child))
      else:
        # print("这不是一个数组（列表）")
        for key, value in component['children'].items():
            if isinstance(key, str):  # Named children
                rendered_children[key] = [generate_html(resolve_component(child)) for child in value]

    return template.render(
        attributes=component.get('attributes', {}),
        config=component.get('config', {}),
        data=component.get('data', {}),
        value=component.get('value', []),
        content=component.get('content', ''),
        files=component.get('files', []),
        cols=component.get('cols', {}),
        children=rendered_children,
        icons=gv.icons,
        classes=gv.classes,
        min=min,
        site_name='7777',
        format_attr=format_attr,
        format_children=format_children
    )

def format_attr(attributes):
  s = ''
  if attributes:
    for attr, value in attributes.items():
        #if attr not in ['class']:
        s+=f' {attr}="{value}" '
  return s
  
def format_children(children):
  s = ''
  if children:
    for child in children:
      print(child)
      s += child
  return s
  
# 辅助函数：解析组件引用
def resolve_component(comp):
    if isinstance(comp, dict) and '$ref' in comp:
        return gv.component_dict[comp['$ref']]
    return comp

# 修改加载配置函数
def load_page_config(config_name = None) -> Dict[str, Any]:
    # config = yaml.safe_load(YAML_CONFIG)
    gv.YAML_CONFIG = load_data_from_yaml(config_name)
    config = copy.deepcopy(gv.YAML_CONFIG)
    # # print(config)
    gv.component_dict = {
        comp['id']: comp 
        for comp in config.get('component_definitions', {}).values()
    }
    
    def resolve_components(components):
        resolved = []
        for comp in components:
            if isinstance(comp, dict) and '$ref' in comp:
                resolved.append(resolve_component(comp))
            elif isinstance(comp, dict) and 'children' in comp:
                resolved_comp = comp.copy()
                resolved_comp['children'] = resolve_components(comp['children'])
                resolved.append(resolved_comp)
            else:
                resolved.append(comp)
        return resolved

    config['components'] = resolve_components(config['components'])
    
    return config

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
def generate_all_configs(engine):
    inspector = inspect(engine)
    
    # Generate config for tables
    for table_name in inspector.get_table_names():
        generate_table_or_view_config(engine, table_name)
    
    # Generate config for views
    for view_name in inspector.get_view_names():
        generate_table_or_view_config(engine, view_name, is_view=True)

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

def get_primary_key(table):
    try:
      return next(iter(table.primary_key.columns)).name
    except Exception as e:
      return None
    
def get_table_names():
    inspector = inspect(engine)
    return inspector.get_table_names()

def get_view_names():
    inspector = inspect(engine)
    return inspector.get_view_names()

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

def get_table_data(
        request: Request = None, 
        table_name: str = None, 
        page: int = 1, 
        page_size: int = 5,
        sort_column: str | None = None,
        sort_direction: str = 'asc'
    ):
    # print('get_table_data')
    
    # print(table_name)

    if request is None:
        request = gv.request
    
    search_params = {}
    if request:
        # Get query parameters from request
        # 从请求中获取查询参数
        search_params = dict(request.query_params)
        
        # print('*****************')
        # print(search_params)
        # print('*****************')

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

    # print(table_name)

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

    table_config = get_table_config(table_name)
    
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
                query = apply_search_filter(query, table, column_config, search_params[column_config['name']])
    
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
    
    # # print('***********************')
    # # print('sort_direction')
    # # print(sort_direction)
    # # print('***********************')
    
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

load_data()

gv.tables = get_tables()

generate_all_configs(engine)

# 主渲染函数保持不变
@app.get("/", response_class=HTMLResponse)
# async def home(request: Request, current_user: dict = Depends(get_current_user)):
#     logger.debug(f"Home page requested. Current user: {current_user}")
    
#     if not current_user:
#         logger.info("Unauthenticated user redirected to login")
#         return RedirectResponse(url="/login", status_code=302)
async def home(request: Request):
    
    gv.request = request
    
    load_data()

    page_config = load_page_config()
    rendered_components = [generate_html(component) for component in page_config['components']]

    template = Template(gv.BASE_HTML)
    return template.render(
        page_title=page_config['title'],
        components=rendered_components,
        min=min
    )

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
    load_data()

    # Load login page configuration
    # 加载登录页面配置
    page_config = load_page_config('login_config.yaml')
    
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

        # # print(result)
            
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
    
    load_data()  # 重新加载配置，确保使用最新的配置

    page_config = load_page_config('register_config.yaml')
    
    rendered_components = [generate_html(component) for component in page_config['components']]

    template = Template(gv.BASE_HTML)
    return template.render(
        page_title="User Management",
        components=rendered_components,
        min=min
    )

@app.post("/register", response_class=HTMLResponse)
async def register(request: Request):
    # print('------------------------')
    # print('register')
    # print('------------------------')
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

    load_page_config()

    res = generate_html(gv.component_dict[component_id])
    return res

@app.get("/tables")
async def read_root(request: Request):
    tables = get_table_names()
    return templates.TemplateResponse("all_in_one.html", {"request": request, "tables": tables})

@app.get("/table/{table_name}")
async def read_table(request: Request, table_name: str):
    # print(str)
    # print(gv.models)
    if table_name not in gv.models:
        raise HTTPException(status_code=404, detail="Table not found")
    
    table_config = get_table_config(table_name)
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

    table_config = get_table_config(table_name)
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
            query = apply_search_filter(query, table, column_config, search_params[column_config['name']])
    
    # Apply sorting if a sort column is specified
    if sort_column and sort_column in table.columns:
        sort_func = desc if sort_direction.lower() == 'desc' else asc
        query = query.order_by(sort_func(getattr(table.c, sort_column)))
    
    with SessionLocal() as session:
        count_query = select(func.count()).select_from(query.alias())
        total_items = session.execute(count_query).scalar()
        result = session.execute(query.offset(offset).limit(page_size)).fetchall()
        
    total_pages = (total_items + page_size - 1) // page_size
    
    # # print('***********************')
    # # print('sort_direction')
    # # print(sort_direction)
    # # print('***********************')

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
    
@app.get("/create", response_class=HTMLResponse)
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
    
    # if id is None:
    #   id = 22

    table_config = get_table_config(table_name)
    
    primary_key = None
    
    
    if True:
      
        #data = dict(result)
        
        component_id = None
    
        if 'component_id' in query_params:
          component_id = query_params['component_id']
        
        if component_id is None:
          component_id = 'form_create'
          
        load_page_config()

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
async def create_item(table_name: str, request: Request):
    # print('post create_item')
    table = None
    if table_name in metadata.tables:
        table = metadata.tables[table_name]
    if table is None:
        raise HTTPException(status_code=404, detail="Table not found")

    form_data = await request.form()
    data = {key: value for key, value in form_data.items() if key in table.columns.keys()}
    
    table_config = get_table_config(table_name)
    
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
            
    
    # for key in data:
    #     data[key] = convert_value(table.c[key].type, data[key])

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
            "primary_key": get_primary_key(table),
            "page": 1,
            "page_size": 10,
            "total_items": session.execute(select(func.count()).select_from(table)).scalar(),
            "total_pages": 1,
            "search": "",
        })
    except SQLAlchemyError as e:
        # print(str(e))
        return {"success": False, "message": str(e)}

@app.get("/edit", response_class=HTMLResponse)
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

    table_config = get_table_config(table_name)
    # # print('table_config')
    # # print(table_config)
    table = metadata.tables[table_name]
    
    primary_key = next((c['name'] for c in table_config['columns'] if c['primary_key'] == 1), None)
    # # print(primary_key)

    if primary_key is None:
        primary_key = get_primary_key(table)
     
    with SessionLocal() as session:
        stmt = select(table).where(getattr(table.c, primary_key) == id)
        result = session.execute(stmt).fetchone()._asdict()
    
    if result:
      
        data = dict(result)
        
        # # print('###############')
        # # print(data)
        # # print('###############')
        
        component_id = None
    
        if 'component_id' in query_params:
          component_id = query_params['component_id']
        
        if component_id is None:
          component_id = 'form_edit'
          
        load_page_config()

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
async def edit_item(table_name: str, id: str, request: Request):
    # print('edit_item')
    # if table_name not in metadata.tables:
    #     raise HTTPException(status_code=404, detail="Table not found")
    # table = metadata.tables[table_name]

    table = None
    if table_name in metadata.tables:
        table = metadata.tables[table_name]
    if table is None:
        raise HTTPException(status_code=404, detail="Table not found")

    primary_key = get_primary_key(table)
    form_data = await request.form()
    data = {key: value for key, value in form_data.items() if key in table.columns.keys()}
    
    table_config = get_table_config(table_name)

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
        print(e)
        return {"success": False, "message": str(e)}

@app.get("/delete", response_class=HTMLResponse)
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
    
    if id is None:
      id = 22

    table_config = get_table_config(table_name)
    
    table = metadata.tables[table_name]

    primary_key = get_primary_key(table)
     
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
          
        load_page_config()

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
async def delete_item(table_name: str, id: str):
    # if table_name not in metadata.tables:
    #     raise HTTPException(status_code=404, detail="Table not found")
    # table = metadata.tables[table_name]

    table = None
    if table_name in metadata.tables:
        table = metadata.tables[table_name]
    if table is None:
        raise HTTPException(status_code=404, detail="Table not found")

    primary_key = get_primary_key(table)
    
    try:
        with SessionLocal() as session:
            stmt = delete(table).where(getattr(table.c, primary_key) == id)
            session.execute(stmt)
            session.commit()
        # return {"success": True, "message": "Item deleted successfully"}
        return "Item deleted successfully"
    except SQLAlchemyError as e:
        return {"success": False, "message": str(e)}

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
    primary_key = get_primary_key(table)
    
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


# 定义允许的文件类型和最大文件大小
ALLOWED_EXTENSIONS = {'.txt', '.pdf', '.png', '.jpg', '.jpeg', '.gif'}
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5 MB

def allowed_file(filename: str) -> bool:
    return os.path.splitext(filename)[1].lower() in ALLOWED_EXTENSIONS

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
    
    
@app.post("/upload", response_class=HTMLResponse)
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
            print('1111')
            result = TM.execute_transactions(
                transaction_name='file_operations',
                params=transaction_params,
                config_file='file_operations_txn.yaml'
            )
            print('2222')
            
            # # 删除临时文件
            # os.remove(temp_file_path)
            
            # 根据结果返回适当的响应
            if isinstance(result, dict) and 'filename' in result:
                load_page_config()
                # # print(gv.component_dict.keys())
                res = generate_html(gv.component_dict['file_manager'])
                res = f'''
                <div hx-swap-oob="innerHTML:#file-manager">
                    {res}
                </div>
                '''
                # # print(res)
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
    # print('get_files')
    files = os.listdir("uploaded")
    return files

@app.get("/preview/{filename}", response_class=HTMLResponse)
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

@app.get("/api/stats", response_class=HTMLResponse)
async def get_stats(request: Request):
    '''
    import plotly.express as px
    fig = px.scatter(x=[0, 1, 2, 3, 4], y=[0, 1, 4, 9, 16])
    # fig.show()
    return fig.to_html(full_html=False, include_plotlyjs=False)
    '''
    return HTMLResponse(f"<div class='error'>{datetime.now().strftime('%Y年%m月%d日 %H:%M:%S')}</div>")

@app.get("/api/total_albums", response_class=HTMLResponse)
async def get_total_albums(request: Request):
    with SessionLocal() as db:
      result = TM.execute_transactions(
                transaction_name = 'get_total_albums',
                config_file="main_txn.yaml"
            )
    return HTMLResponse(str(result[0]['total_albums']))

@app.get("/api/total_artists", response_class=HTMLResponse)
async def get_total_albums(request: Request):
    with SessionLocal() as db:
      result = TM.execute_transactions(
                transaction_name = 'get_total_artists',
                config_file="main_txn.yaml"
            )
    return HTMLResponse(str(result[0]['total_artists']))
   
@app.get("/setup_customer_database", response_class=HTMLResponse)
async def setup_customer_database(request: Request):
    with SessionLocal() as db:
      result = TM.execute_transactions(
                transaction_name = 'setup_customer_database',
                config_file="table_management_txn.yaml"
            )
    return HTMLResponse(str(result[0]['total_artists']))

@app.get("/database_management", response_class=HTMLResponse)
async def database_management(request: Request):
    with SessionLocal() as db:
      result = TM.execute_transactions(
                transaction_name = 'create_new_database',
                config_file="database_management_txn.yaml"
            )
    return HTMLResponse(str(result[0]['total_artists']))
 
@app.get("/project_management_system", response_class=HTMLResponse)
async def project_management_system(request: Request):
    with SessionLocal() as db:
      result = TM.execute_transactions(
                transaction_name = 'create_base_tables',
                config_file="project_management_system_txn.yaml"
            )
    # print(result)
    return HTMLResponse('end')

@app.get("/initialize_base_data", response_class=HTMLResponse)
async def initialize_base_data(request: Request):
    with SessionLocal() as db:
      result = TM.execute_transactions(
                transaction_name = 'initialize_base_data',
                config_file="project_management_system_txn.yaml"
            )
    # print(result)
    #return HTMLResponse(str(result[0]['total_artists']))
    return HTMLResponse('end')

@app.get("/pms", response_class=HTMLResponse)
async def initialize_base_data(request: Request):
    with SessionLocal() as db:
        # result = TM.execute_transactions(
        #             transaction_name = 'create_new_project',
        #             config_file="project_management_system_txn.yaml"
        #         )
        # # print(result)
        # result = TM.execute_transactions(
        #             transaction_name = 'add_project_member',
        #             params={
        #                 'project_id': 1,
        #                 'user_id': 1
        #             },
        #             config_file="project_management_system_txn.yaml"
        #         )
        # # print(result)
        # result = TM.execute_transactions(
        #             transaction_name = 'create_new_issue',
        #             params={
        #                 'subject': 'prj1'
        #             },
        #             config_file="project_management_system_txn.yaml"
        #         )
        # # print(result)
        # result = TM.execute_transactions(
        #             transaction_name = 'update_issue_status',
        #             params={
        #                 'new_status_id': 3,
        #                 'issue_id': 1,
        #                 'current_user_id': 1,
        #                 'new_status_name': 'In Progress'
        #             },
        #             config_file="project_management_system_txn.yaml"
        #         )
        # # print(result)
        '''
        result = TM.execute_transactions(
                    transaction_name = 'log_time_entry',
                    params={
                        'issue_id': 1,
                        'user_id': 1,
                        'hours': 1,
                        'comments': 'コメント',
                        'spent_on': "{{ current_timestamp }}", #spent_on
                        'created_at': "{{ current_timestamp }}",
                        'updated_at': "{{ current_timestamp }}",
                    },
                    config_file="project_management_system_txn.yaml"
                )
        # print(result)
        '''
        # result = TM.execute_transactions(
        #             transaction_name = 'get_project_statistics',
        #             params={
        #                 'project_id': 1
        #             },
        #             config_file="project_management_system_txn.yaml"
        #         )
        # # print(result)
        # result = TM.execute_transactions(
        #             transaction_name = 'create_new_database',
        #             config_file="database_management_txn.yaml"
        #         )
        # # print(result)

        # Database connection configuration
        DATABASE_URL1 = "sqlite:///./project_management.db"
        # Reflect existing database tables
        TM1 = TransactionModule(database_url = DATABASE_URL1)

        # result = TM1.execute_transactions(
        #             transaction_name = 'create_base_tables',
        #             config_file="project_management_system_txn.yaml"
        #         )
        # # print(result)
        
        # result = TM1.execute_transactions(
        #         transaction_name = 'create_new_project',
        #         config_file="project_management_system_txn.yaml"
        #     )
        # # print(result)
        
        result = TM1.execute_transactions(
                    transaction_name = 'add_project_member',
                    params={
                        'project_id': 1,
                        'user_id': 1
                    },
                    config_file="project_management_system_txn.yaml"
                )
        # # print(result)
        
    return HTMLResponse('end')
    
@app.get("/cms", response_class=HTMLResponse)
async def initialize_base_data(request: Request):
    # 7with SessionLocal() as db:

        # result = TM.execute_transactions(
        #           transaction_name = 'create_new_database',
        #           config_file="cms.yaml"
        #       )
        # # print(result)
    
        # # Database connection configuration
        # DATABASE_URL1 = "sqlite:///./cms.db"
        # # Reflect existing database tables
        # TM1 = TransactionModule(database_url = DATABASE_URL1)
        
        # result = TM1.execute_transactions(
        #             transaction_name = 'create_base_tables',
        #             config_file="cms.yaml"
        #         )
        # # print(result)
        
    # result = TM.execute_transactions(
    #             transaction_name = 'initialize_base_data',
    #             params={
    #                 'hashed_password': '$2b$12$owwC890GCP59/Jsks0tz1eG4C9Z6hDpI1O/hHvsEhiINxvO/rQ.Qe'
    #             },
    #             config_file="cms.yaml"
    #         )
    result = TM.execute_transactions(
                transaction_name = 'create_post',
                params={
                  'title': "3rd post",
                  'slug': "3rd-post",
                  'content': "This is my 3rd post!"
                },
                config_file="cms.yaml"
            )
    # # print(result)

    # result = TM.execute_transactions(
    #             transaction_name = 'get_posts_list',
    #             # params={
    #             #   'title': "2nd post",
    #             #   'slug': "2nd-post",
    #             #   'content': "This is my 2nd post!"
    #             # },
    #             config_file="cms.yaml"
    #         )
    # # print(result)
    
    return HTMLResponse('end')

# 主渲染函数保持不变
@app.get("/blog", response_class=HTMLResponse)
async def get_blog(request: Request):
    
    gv.request = request

    query_params = dict(request.query_params)
    if query_params is None:
      query_params = []

    if 'api' in query_params:
        if 'posts' == query_params['api']:
          return await get_posts(request)
        elif 'post' == query_params['api']:
          return await get_post(request)
        elif 'edit' == query_params['api']:
          return await get_post_form(request)
    '''
    if 'posts' in query_params:
      return await get_posts(request)
    elif 'post' in query_params:
      return await get_post(request)
    elif 'edit' in query_params:
      return await get_post_form(request)
    '''
    
    load_data()

    posts_config = get_table_config('posts')
    gv.posts_config = posts_config
      
    page_config = load_page_config('blog_config.yaml')
    
    hx_get = '/blog'
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
        'hx-get': hx_get,
        'hx-swap': 'innerHTML',
        'hx-trigger': 'load, newPost from:body, updatePost from:body, deletePost from:body',
        'hx-url': hx_get
    }
    gv.component_dict['blogs']['attributes'] = gv.component_dict['blogs']['attributes'] | blogs_attr

    rendered_components = [generate_html(component) for component in page_config['components']]

    template = Template(gv.BASE_HTML)
    h = template.render(
        page_title=page_config['title'],
        components=rendered_components,
        min=min
    )

    return h

@app.get("/blog/posts", response_class=HTMLResponse)
async def get_posts(request: Request):

    if "HX-Request" in request.headers:
        #print(request.headers)
        pass
      
    query_params = dict(request.query_params)

    search_term = str(query_params['search_term']) if 'search_term' in query_params else ''
    page_size = int(query_params['page_size']) if 'page_size' in query_params else 5
    page_number = int(query_params['page_number']) if 'page_number' in query_params else 1

    result = TM.execute_transactions(
                transaction_name = 'get_posts_list',
                params={
                    'search_term': '%' + search_term + '%',
                    'limit': page_size,
                    'offset': (page_number - 1) * page_size
                },
                config_file="cms.yaml"
            )
            
    result = [dict(row) for row in result]  # 转换为字典列表

    no_next = False
    if len(result) < page_size:
        no_next = True
    
    no_prev = False
    if page_number <= 1:
        no_prev = True

    h = ''
    try:
        load_page_config('blog_config.yaml')

        for d in result:
          d['attributes'] = {
            'del': {
              'hx-delete': f"/blog/post?post_id={d['id']}&post" 
            },
            'edit': {
              'hx-post': f"/blog/post/form?post_id={d['id']}&post",
              'hx-target': '#form_container'
            },
            'go': {
              'hx-get': f"/blog/post?post_id={d['id']}&post",
              'hx-target': '#blogs'
            }
          }
          
        gv.component_dict['posts']['data'] = result

        hx_url = f"/blog?search_term={search_term}&page_size={page_size}&page_number={page_number - 1}"
        hx_get = hx_url + '&api=posts'

        prev_attr = {
                    'id': 'prev',
                    'hx-get': hx_get, 
                    'hx-swap': 'innerHTML',
                    'hx-target': '#blogs',
                    'hx-url': hx_url,
                }
        if no_prev:
            prev_attr['disabled'] = True

        hx_url = f"/blog?search_term={search_term}&page_size={page_size}&page_number={page_number + 1}"
        hx_get = hx_url + '&api=posts'

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
        }
        #print(gv.component_dict['posts'])
        h = generate_html(gv.component_dict['posts'])
    except Exception as e:
        print(e)

    return HTMLResponse(content=h)
    
@app.get("/blog/post", response_class=HTMLResponse)
async def get_post(request: Request):
    print('get_post')
    print(request)
    #return('666')
    if "HX-Request" in request.headers:
        #print(request.headers)
        #print(request.headers['hx-current-url'])
        pass
      
        parsed_url = urlparse(request.headers['hx-current-url'])
        print(parsed_url)

    query_params = dict(request.query_params)

    if 'post_id' not in query_params:
      return 'no data'
      
    post_id = int(query_params['post_id'])
    print(post_id)
    #return 'ok'
    result = TM.execute_transactions(
                transaction_name = 'get_post_detail',
                params={
                    'post_id': post_id
                },
                config_file="cms.yaml"
            )
    result = [dict(row) for row in result]  # 转换为字典列表
    #print(result)
    
    h = ''
    try:
        load_page_config('blog_config.yaml')
        gv.component_dict['post']['data'] = result

        gv.component_dict['post']['config'] = {
            'back': {
                'attributes': {
                    'hx-get': f'{parsed_url.path}?{parsed_url.query}&api=posts',
                }
            }
        }
        h = generate_html(gv.component_dict['post'])
    except Exception as e:
        print(e)

    return HTMLResponse(content=h)

    
@app.post("/blog/post/form", response_class=HTMLResponse)
async def get_post_form(request: Request):
    print('get_post form')

    if "HX-Request" in request.headers:
        #print(request.headers)
        #print(request.headers['hx-current-url'])
        pass

    parsed_url = urlparse(request.headers['hx-current-url'])
    #print(parsed_url)

    query_params = dict(request.query_params)
    print(query_params)
    
    result = []
    
    if 'post_id' in query_params:
      #return 'no data'
      
      post_id = int(query_params['post_id'])
   
      result = TM.execute_transactions(
                  transaction_name = 'get_post_detail',
                  params={
                      'post_id': post_id
                  },
                  config_file="cms.yaml"
              )
      result = [dict(row) for row in result]  # 转换为字典列表
      #print(result)
    
      h = ''
      try:
          if len(result) > 0:
              load_page_config('blog_config.yaml')
              gv.component_dict['form_edit']['data'] = result[0]
              
              h = generate_html(gv.component_dict['form_edit'])
      except Exception as e:
          print(e)
  
      return HTMLResponse(content=h)
      
    else:
      
      h = ''
      try:
          if True:
              load_page_config('blog_config.yaml')
              gv.component_dict['form_edit']['data'] = result
              
              h = generate_html(gv.component_dict['form_create'])
      except Exception as e:
          print(e)
  
      return HTMLResponse(content=h)

      
@app.post("/blog/post", response_class=HTMLResponse)
async def post_blog_post(request: Request):
    print('post_blog_post')
    form_data = await request.form()
    #print(form_data)
    #print(form_data['featured_image'])
    file = form_data.get('featured_image')
    
    #print(file)
    result = TM.execute_transactions(
                transaction_name = 'create_post',
                params={
                  'title': form_data['title'],
                  'slug': "slug",
                  'content': form_data['content'],
                  'status': form_data['status'],
                  #'file': form_data['featured_image']
                  "file": file,
                  "file_name": file.filename,
                  "folder_path": "./uploaded"
                },
                config_file="cms.yaml"
            )
            
    headers = {"HX-Trigger": "newPost"}
    return HTMLResponse(content='ok', headers=headers)

@app.put("/blog/post", response_class=HTMLResponse)
async def put_blog_post(request: Request):
    print('put_blog_post')
    form_data = await request.form()
    print(form_data)
    file = form_data.get('featured_image')
    
    result = TM.execute_transactions(
                transaction_name = 'update_post',
                params={
                    'id': form_data['id'],
                    'title': form_data['title'],
                    'content': form_data['content'],
                    'status': form_data['status'],
                    "file": file,
                    "file_name": file.filename,
                    "folder_path": "./uploaded"
                },
                config_file="cms.yaml"
            )
            
    headers = {"HX-Trigger": "updatePost"}
    return HTMLResponse(content='ok', headers=headers)

@app.delete("/blog/post", response_class=HTMLResponse)
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

@app.get("/test", response_class=HTMLResponse)
async def blog(request: Request):
    
    gv.request = request

    query_params = dict(request.query_params)
    #print(query_params)

    load_data()

    page_config = load_page_config('test_config.yaml')

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
    #print(query_params)

    return str(query_params);
    
if __name__ == "__main__":
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
