import os
import sys
import re
import uvicorn
import json
import inspect
from pathlib import Path
from urllib.parse import unquote

import traceback

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

from gv import *
import gv as gv
import transaction_module
from transaction_module import convert_value, TransactionModule

from DatabaseManager import DatabaseManager
from ConfigManager import ConfigManager

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
templates.env.globals['site_name'] = ''

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

@app.api_route("/{any_path:path}", response_class=HTMLResponse, methods=['GET', 'POST', 'PUT', 'DELETE'])
async def universal_handler(any_path: str, request: Request):
    
    gv.request = request

    try:
        any_path = any_path.rstrip('/')
        full_path = request.url.path.rstrip('/')
        #print('-----------full_path-----------')
        #print(any_path)
        #print(full_path)
        #print('-----------full_path-----------')

        # 获取 HTTP 方法
        http_method = request.method

        # 判断请求方法
        if http_method == "GET":
            pass
        elif http_method == "POST":
            if full_path == '/blog/post/comment':
                return await BlogManager.post_blog_post_comment(request)
            if full_path == '/blog/post':
                return await BlogManager.post_blog_post(request)
            pass
        #    #eturn f"Received a POST request at path: {any_path}"
        # elif http_method == "PUT":
        #     return f"Received a PUT request at path: {any_path}"
        elif http_method == "DELETE":
            if full_path == '/blog/post/comment':
                return await BlogManager.post_blog_post_comment(request)
            if full_path == '/blog/posts':
                return await BlogManager.delete_blog_post(request)
            pass
        #     #return f"Received a DELETE request at path: {any_path}"
        # elif http_method == "PATCH":
        #     return f"Received a PATCH request at path: {any_path}"
        # else:
        #     return f"Received an unknown method ({http_method}) at path: {any_path}"

        if request.url.path == '/':
            return await CustomRenderer.get(request)

        if request.url.path == '/blog/post/comments':
            return await BlogManager.get_blog_post_comments(request)

        if request.url.path == '/api/blog/categories':
            return await BlogManager.get(request)

        if request.url.path == '/api/blog/tags':
            return await BlogManager.get(request)

        if request.url.path == '/api/blog/users':
            return await BlogManager.get(request)

        if request.url.path == '/component':
            return await rendered_component(request)

        if request.url.path == '/edit':
            return await edit_form(request)

        if request.url.path == '/blog/post/form':
            return await BlogManager.get_post_form(request)
            
        if request.url.path == '/blog/posts':
            is_htmx_request = request.headers.get("HX-Request") == "true"
            if is_htmx_request:
                return await BlogManager.get_posts(request)
            else:
                await BlogManager.get_blog(request)
        
        if request.url.path == '/blog':
            return await BlogManager.get_blog(request)
        if request.url.path == '/blog/settings':
            return await CustomRenderer.get(request)
        if request.url.path == '/blog/about':
            return await CustomRenderer.get(request)

        return full_path

    except Exception as e:
        eee(e)

class BlogManager:

    @staticmethod
    def get_query_paramas(request, PRMS = None):
        #print('get_query_paramas')
        #print('PRMS')
        #print(PRMS)
        try:
            query_params = {}
            if request.query_params:
                query_params = dict(request.query_params)
                #print('-------------')
                #print(query_params)
                for k, v in query_params.items():                
                    if v:
                        try:
                            # 尝试解析为整数
                            v = int(v)
                        except ValueError:
                            try:
                                # 尝试解析为浮点数
                                v = float(v)
                            except ValueError:
                                pass
                        query_params[k] = v
                #print('PRMS')
                #print(PRMS)
                if PRMS:
                    PRMS.update(query_params)
                    query_params = PRMS
                    
                #print('PRMS')
                #print(PRMS)
                #print('-------------')
            else:
                if PRMS:
                    query_params = PRMS
                
            return query_params
        except Exception as e:
            eee(e)

    @staticmethod
    def get_formatted_url(url, query_params):
        try:
          
            '''
            # 使用正则表达式提取占位符
            placeholders = re.findall(r'\{(.*?)\}', url)
            
            # 动态替换
            formatted_url = url
            for placeholder in placeholders:
                v = ''
                if placeholder in query_params:
                    v = str(query_params[placeholder])
                formatted_url = formatted_url.replace(f'{{{placeholder}}}', v)
            '''
            
            # 自定义替换函数
            def replace_expression(match):
                expression = match.group(1)  # 提取表达式
                if ' - ' in expression:
                    var, offset = expression.split(' - ')
                    return str(query_params.get(var, 0) - int(offset))
                elif ' + ' in expression:
                    var, offset = expression.split(' + ')
                    return str(query_params.get(var, 0) + int(offset))
                else:
                    print(expression)
                    print(query_params)
                    return str(query_params.get(expression, ''))
        
            # 使用正则表达式替换
            formatted_url = re.sub(r'\{(.*?)\}', replace_expression, url)

            return formatted_url
        except Exception as e:
            eee(e)

    @staticmethod
    def get_data(query_params):
        try:
            data_name = query_params.get('data_name', '')

            if data_name == '':
                return None
            
            search_term = query_params.get('search_term', '')
            page_size = query_params.get('page_size', 5)
            page_number = query_params.get('page_number', 1)
            
            post_id = query_params.get('post_id', None)

            result = DatabaseManager.tm.execute_transactions(
                transaction_name='get_' + data_name,
                params={
                    'search_term': '%' + search_term + '%',
                    'limit': page_size,
                    'offset': (page_number - 1) * page_size,
                    'post_id': post_id
                },
                config_file="cms.yaml"
            )

            result = gv.data[data_name]

            return result
        except Exception as e:
            eee(e)

    @staticmethod
    async def get_blog(request: Request):
        #print('get_blog')
        try:
            gv.request = request
            
            ConfigManager.load_data()
            
            page_config = PageRenderer.load_page_config('blog_config.yaml')
            
            #print('@@@@@@@@@@@@@@@@')
            rendered_components = [
                PageRenderer.generate_html(component) for component in page_config['components']
            ]
            #print('@@@@@@@@@@@@@@@@')

            template = Template(gv.BASE_HTML)
            h = template.render(
                page_title=page_config['title'],
                components=rendered_components
            )
            
            return HTMLResponse(content=h)

        except Exception as e:
            eee(e)

    @staticmethod
    async def get_posts(request: Request):
        try:
            #print('get_posts')

            ConfigManager.load_data()
            #print('###########@')
            #print(request.query_params)
            query_params = BlogManager.get_query_paramas(request)
            query_params['data_name'] = 'posts'
            #print(query_params)

            result = BlogManager.get_data(query_params)
            #print(result)
            #print('###########@')
            
            gv.component_dict['posts']['data'] = result
            
            h = PageRenderer.generate_html(gv.component_dict['posts'], 'posts')
            
            response = HTMLResponse(content=h)
            return response
            
        except Exception as e:
            eee(e)

    @staticmethod
    async def get_post_form(request: Request):
        try:
            #print('get_post_form')

            gv.request = request

            ConfigManager.load_data()

            query_params = dict(request.query_params)

            result = []

            if 'post_id' in query_params:

                post_id = int(query_params['post_id'])

                result = DatabaseManager.tm.execute_transactions(
                    transaction_name='get_post_detail',
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

                        h = PageRenderer.generate_html(
                            gv.component_dict['form_edit'])
                except Exception as e:
                    eee(e)

                return HTMLResponse(content=h)

            else:

                h = ''
                try:
                    if True:
                        PageRenderer.load_page_config('blog_config.yaml')
                        gv.component_dict['form_edit']['data'] = result
                        # #print(gv.component_dict['form_edit'])
                        h = PageRenderer.generate_html(
                            gv.component_dict['form_edit'])

                        ##print(h)
                except Exception as e:
                    eee(e)

                return h
                return HTMLResponse(content=h)

        except Exception as e:
            eee(e)

    @staticmethod
    async def get(request: Request):
        try:
            gv.request = request

            # 获取 URL 路径
            full_path = request.url.path

            # 去除末尾的斜杠，然后按 "/" 分割路径
            path_parts = full_path.rstrip("/").split("/")

            # 获取最后一个部分作为 page_name
            page_name = unquote(path_parts[-1]) if path_parts else ""

            query_params = dict(request.query_params)

            # page_config = PageRenderer.load_page_config(page_name + '_config.yaml')
            # PRMS = page_config['const']['params']
            # query_params = BlogManager.get_query_paramas(request, PRMS)

            query_params['data_name'] = page_name

            result = BlogManager.get_data(query_params)

            gv.component_dict[page_name]['data'] = result

            h = PageRenderer.generate_html(gv.component_dict[page_name], page_name)

            return HTMLResponse(content=h)

        except Exception as e:
            eee(e)

    @staticmethod
    async def get_blog_post_comments(request: Request):
        try:

            gv.request = request

            ConfigManager.load_data()

            query_params = dict(request.query_params)

            search_term = str(
                query_params['search_term']) if 'search_term' in query_params else ''
            page_size = int(query_params['page_size']
                            ) if 'page_size' in query_params else 5
            page_number = int(
                query_params['page_number']) if 'page_number' in query_params else 1
            post_id = int(query_params['post_id']
                          ) if 'post_id' in query_params else None

            result = DatabaseManager.tm.execute_transactions(
                transaction_name='get_post_comments',
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

            h = PageRenderer.generate_html(gv.component_dict['comment'], 'comment')

            return HTMLResponse(content=h)

        except Exception as e:
            eee(e)

    @staticmethod
    async def post_blog_post(request: Request):
        try:
            form_data = await request.form()
            file = form_data.get('featured_image')

            result = DatabaseManager.tm.execute_transactions(
                transaction_name='create_post',
                params={
                    'title': form_data['title'],
                    'slug': "slug",
                    'content': form_data['content'],
                    'status': form_data['status'],
                    # 'file': form_data['featured_image']
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

        except Exception as e:
            eee(e)

    @staticmethod
    async def put_blog_post(request: Request):
        try:
            form_data = await request.form()
            file = form_data.get('featured_image')

            result = DatabaseManager.tm.execute_transactions(
                transaction_name='update_post',
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

        except Exception as e:
            eee(e)

    @staticmethod
    async def delete_blog_post(request: Request):
        try:
            #print('delete_blog_post')
            query_params = dict(request.query_params)

            result = DatabaseManager.tm.execute_transactions(
                transaction_name='delete_post',
                params={
                    'id': query_params['post_id']
                },
                config_file="cms.yaml"
            )

            headers = {"HX-Trigger": "deletePost"}
            return HTMLResponse(content='ok', headers=headers)

        except Exception as e:
            eee(e)

    @staticmethod
    async def post_blog_post_comment(request: Request):
        try:

            form_data = await request.form()

            result = DatabaseManager.tm.execute_transactions(
                transaction_name='add_comment',
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

        except Exception as e:
            eee(e)

class PageRenderer:
    """页面渲染管理类"""
    templates_env = Environment(loader=FileSystemLoader("templates"))

    @staticmethod
    def resolve_component(comp):
        try:
            if isinstance(comp, dict) and '$ref' in comp:
                return gv.component_dict[comp['$ref']]
            return comp

        except Exception as e:
            eee(e)

    # 修改加载配置函数
    @staticmethod
    def load_page_config(config_name=None) -> Dict[str, Any]:
        try:
            # config = yaml.safe_load(YAML_CONFIG)
            gv.YAML_CONFIG = ConfigManager.load_data_from_yaml(config_name)
            config = copy.deepcopy(gv.YAML_CONFIG)

            # 合并所有基础数据
            all_base_data = ConfigManager.deep_merge(gv.base_config, config)

            # 解析继承关系
            resolved_data = ConfigManager.resolve_inheritance(
                config, all_base_data)
                
            # 将 base_data 中不冲突的部分合并到最终结果中
            final_data = ConfigManager.deep_merge(
                gv.base_config, resolved_data)
            config = final_data
            
            gv.component_dict = config.get('component_definitions', {})
            
            def resolve_components(components):
                resolved = []
                for comp in components:
                    if isinstance(comp, dict) and '$ref' in comp:
                        resolved.append(PageRenderer.resolve_component(comp))
                    elif isinstance(comp, dict) and 'children' in comp:
                        resolved_comp = comp.copy()
                        resolved_comp['children'] = PageRenderer.resolve_components(
                            comp['children'])
                        resolved.append(resolved_comp)
                    else:
                        resolved.append(comp)
                return resolved
                
            config['components'] = resolve_components(config['components'])
            
            return config

        except Exception as e:
            eee(e)

    @staticmethod
    def generate_html(component: Dict[str, Any], page_name='') -> str:
        try:
            if 'type' not in component:
                component['type'] = 'div'

            for key in ['config', 'data', 'value', 'files']:
                if key in component and isinstance(component[key], str):
                    if '.' in component[key]:
                        k = component[key].split('.')
                        if len(k) == 2:
                            ##print(k)
                            # 获取类
                            cls = globals()[k[0]]
                            # 获取静态方法并调用
                            component[key] = getattr(cls, k[1])()
                    pass

            # #print('3')
            if 'cols' in component:
                #print('🍺🍺🍺🍺🍺🍺🍺🍺')
                #print(component['cols'])
                #print('🍺🍺🍺🍺🍺🍺🍺🍺')
                
                for key in component['cols']:
                    if component['type'] == 'form_base_type_1':
                        #print('😭😭😭😭😭😭😭😭')
                        #print(key)
                        #print(component['cols'][key])
                        #print('😭😭😭😭😭😭😭😭')
                        
                        config_id = component['config']['id'] + '_config'
                        if hasattr(gv, config_id):
                            pass
                        else:
                            setattr(gv, config_id, ConfigManager.get_table_config(
                                component['config']['id']))
                  
                        config = getattr(gv, config_id)
                        if 'cols' in config and key in config['cols']:
                            component['cols'][key] = config['cols'][key] | component['cols'][key]
                        
                        #print('😎😎😎😎😎😎😎😎')
                        #print(key)
                        #print(component['cols'][key])
                        #print('😎😎😎😎😎😎😎😎')
                        
                        if 'value' in component['cols'][key]:
                            value = component['cols'][key]['value']
                            component['cols'][key]['value'] = None
                            ##print(key)
                            ##print(component['cols'])
                            #'''
                            print('🙄🙄🙄🙄🙄🙄🙄🙄🙄')
                            print(key)
                            print(value)
                            #print(gv.data)
                            if value:
                              print(value)
                              k = value.split('.')
                              if len(k) == 2:
                                  print(k)
                                  print(component['data'])
                                  if k[0] in gv.data:
                                      print(gv.data[k[0]])
                                      if len(gv.data[k[0]]) > 0:
                                          if k[1] in gv.data[k[0]][0]:
                                              component['cols'][key]['value'] = gv.data[k[0]][0][k[1]]
                            print('🙄🙄🙄🙄🙄🙄🙄🙄🙄')
                            
                            #'''
                        
                        config_id = component['config']['id'] + '_config'
                        if hasattr(gv, config_id):
                            pass
                        else:
                            setattr(gv, config_id, ConfigManager.get_table_config(
                                component['config']['id']))
                        '''
                        config = getattr(gv, config_id)
                        if 'cols' in config and key in config['cols']:
                            component['cols'][key] = config['cols'][key] | component['cols'][key]
                        '''
                    '''
                    else:
                        if 'data_from' in component:
                            if component['data_from'] == 'comments':
                                if gv.comments_config and 'cols' in gv.comments_config and key in gv.comments_config['cols']:
                                    # component['cols'][key] = gv.comments_config['cols'][key]
                                    component['cols'][key] = gv.comments_config['cols'][key] | component['cols'][key]
                        else:
                            if gv.posts_config and 'cols' in gv.posts_config and key in gv.posts_config['cols']:
                                # component['cols'][key] = gv.posts_config['cols'][key]
                                component['cols'][key] = gv.posts_config['cols'][key] | component['cols'][key]
                    '''
            print('>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>')
            print(component['type'])
            print(gv.HTML_TEMPLATES.get(component['type'], ''))
            print('>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>')
            template = Template(gv.HTML_TEMPLATES.get(component['type'], ''))
            rendered_children = {}
            # #print('4')
            if 'children' in component:
                if isinstance(component['children'], list):
                    rendered_children = []
                    for child in component.get('children', []):
                        child = PageRenderer.resolve_component(child)
                        # # if 'data_from' in child and child['data_from'] in component.get('data', {}):
                        # if False:
                        #     child['data'] = component.get(
                        #         'data', {})[child['data_from']]

                        # child['data'] = []
                        # if 'data_from' in child:
                        #     if child['data_from'] in gv.data:
                        #         child['data'] = gv.data.get(child['data_from'], [])

                        # else:
                        #     child['data'] = component.get('data', {})

                        child['data'] = component.get('data', {})
                        print('>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>1111')
                        print(child['data'])
                        print('>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>1111')

                        rendered_children.append(
                            PageRenderer.generate_html(child))
                else:
                    # #print('6')
                    for key, value in component['children'].items():
                        if isinstance(key, str):
                            if value:
                                rendered_children[key] = [PageRenderer.generate_html(
                                    PageRenderer.resolve_component(child)) for child in value]

            data = component.get('data', {})

            h = template.render(
                component=component,
                attributes=component.get('attributes', {}),
                config=component.get('config', {}),
                # data=component.get('data', {}),
                data=data,
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
                format_children=PageRenderer.format_children
            )

            return h
        except Exception as e:
            eee(e)

    @staticmethod
    def format_attr(attributes, data = None, component = None):
        #print('format_attr')
        #print(data)
        #print(component)
        try:
            s = ''
            if attributes:
                for attr, value in attributes.items():
                    if attr == 'hx-get' or attr == 'hx-delete':
                        if value == 'history_back':
                            parsed_url = urlparse(gv.request.headers['hx-current-url'])
                            value = '{}?{}'.format(parsed_url.path, parsed_url.query)
                        else:
                            if data:
                                #print('-----------------data----------')
                                #print(data)
                                #print(value)
                                value = BlogManager.get_formatted_url(value, data)
                                #print(value)
                                #print('-----------------data----------')
                            else:
                                #print('aaa')
                                ##print(PRMS)
                                query_params = BlogManager.get_query_paramas(gv.request)
                                #print(query_params)
                                #print('aaa')
                                if component:
                                    #print('*******************')
                                    PRMS = component.get('const', {}).get('params', {})
                                    #print(PRMS)
                                    query_params = BlogManager.get_query_paramas(gv.request, PRMS.copy())
                                    #print(query_params)
                                    PRMS = component.get('const', {}).get('params', {})
                                    #print(PRMS)
                                    #print('*******************')
                                    
                                value = BlogManager.get_formatted_url(value, query_params)
                    '''
                    else:
                        matches = re.findall(r'\{\{.*?\}\}', value)
                        # 去除多余的空格
                        matches = [match.strip() for match in matches]
                        if matches:
                            param_name = matches[0]
                            k = param_name.replace(
                                '{{', '').replace('}}', '').strip().split('.')
                            if len(k) == 2:
                                if k[0] in gv.data:
                                    if len(gv.data[k[0]]) > 0:
                                        if k[1] in gv.data[k[0]][0]:
                                            value = value.replace(
                                                param_name, str(gv.data[k[0]][0][k[1]]))
                    '''
                    s += f' {attr}="{value}" '
            return s
        except Exception as e:
            eee(e)

    @staticmethod
    def format_children(children):
        try:
            s = ''
            if children:
                for child in children:
                    if child:
                        s += child
            return s
        except Exception as e:
            eee(e)

class CustomRenderer(PageRenderer):
    """继承 PageRenderer 并扩展功能"""

    def __init__(self, template_directory="templates"):
        super().__init__()
        self.templates_env = Environment(
            loader=FileSystemLoader(template_directory))
        self.templates_env.globals['min'] = min  # 可以添加自定义全局函数
        self.templates_env.globals['site_name'] = 'My Custom Site'

    @staticmethod
    async def get(request: Request):
        try:
            ConfigManager.load_data()

            gv.request = request

            full_path = request.url.path

            path_parts = full_path.strip("/").split("/")  # 分解路径为列表

            page_name = path_parts[-1]

            if page_name == '':
                page_name = 'main'

            page_config = PageRenderer.load_page_config(
                page_name + '_config.yaml')

            rendered_components = [PageRenderer.generate_html(
                component) for component in page_config['components']]

            template = Template(gv.BASE_HTML)
            h = template.render(
                page_title=page_config['title'],
                components=rendered_components,
                min=min
            )

            return h

        except Exception as e:
            eee(e)

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
