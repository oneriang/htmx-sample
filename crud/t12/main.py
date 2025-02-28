import os
import sys
import re
import uvicorn
import json
import inspect
from pathlib import Path
from urllib.parse import unquote

import traceback
import math

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

        # 获取 HTTP 方法
        http_method = request.method

        # 判断请求方法
        if http_method == "GET":
            if full_path == '/':
                return await CustomRenderer.get(request)
            if full_path == '/favicon.ico':
                pass
            else:
                if full_path == '/blog':
                    return await BlogManager.get_blog(request)
                elif full_path == '/blog/posts':
                    is_htmx_request = request.headers.get("HX-Request") == "true"
                    if is_htmx_request:
                        return await BlogManager.get(request)
                    else:
                        await BlogManager.get_blog(request)
                elif full_path == '/blog/posts/form':
                    return await BlogManager.get_posts_form(request)
                elif full_path.startswith('/api/blog/'):
                    return await BlogManager.get(request)
                elif full_path == '/blog/post/comments':
                    return await BlogManager.get(request)
                elif full_path == '/component':
                    return await rendered_component(request)
                elif full_path == '/edit':
                    return await edit_form(request)
                else:
                    return await CustomRenderer.get(request)
            pass
        elif http_method == "POST":
            return await BlogManager.post(request)
            pass
        #    #eturn f"Received a POST request at path: {any_path}"
        elif http_method == "PUT":
            return await BlogManager.put(request)
            pass
        #     return f"Received a PUT request at path: {any_path}"
        elif http_method == "DELETE":
            if full_path == '/blog/post/comments':
                return await BlogManager.delete(request)
            if full_path == '/blog/posts':
                return await BlogManager.delete(request)
            pass
        #     #return f"Received a DELETE request at path: {any_path}"
        # elif http_method == "PATCH":
        #     return f"Received a PATCH request at path: {any_path}"
        # else:
        #     return f"Received an unknown method ({http_method}) at path: {any_path}"


        return full_path

    except Exception as e:
        eee(e)

class BlogManager:

    @staticmethod
    def get_query_paramas(request, PRMS = None):
        try:
            query_params = {}
            if request.query_params:
                query_params = dict(request.query_params)
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
                if PRMS:
                    PRMS.update(query_params)
                    query_params = PRMS
            else:
                if PRMS:
                    query_params = PRMS
                
            return query_params
        except Exception as e:
            eee(e)

    @staticmethod
    def get_formatted_url(url, query_params):
        try:
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
                    return str(query_params.get(expression, ''))
        
            # 使用正则表达式替换
            formatted_url = re.sub(r'\{(.*?)\}', replace_expression, url)

            return formatted_url
        except Exception as e:
            eee(e)

    @staticmethod
    def get_data(func_name, query_params):
        try:
            data_name = query_params.get('data_name', '')

            if data_name == '':
                return None
            
            search_term = query_params.get('search_term', '')
            page_size = query_params.get('page_size', 5)
            page_number = query_params.get('page_number', 1)
                        
            result = DatabaseManager.tm.execute_transactions(
                transaction_name=func_name + '_' + 'count',
                params={
                    'search_term': '%' + search_term + '%',
                },
                config_file="cms.yaml"
            )
            print('😀😀😀😀😀😀😀')
            total_count = result[0]['count']
            page_count = math.ceil(total_count / page_size)
            query_params['total_count'] = total_count
            query_params['page_count'] = page_count
            print(query_params)
            print('😀😀😀😀😀😀😀')
            
            id = query_params.get('id', None)

            result = DatabaseManager.tm.execute_transactions(
                transaction_name=func_name,
                params={
                    'search_term': '%' + search_term + '%',
                    'limit': page_size,
                    'offset': (page_number - 1) * page_size,
                    'id': id
                },
                config_file="cms.yaml"
            )

            result = gv.data[data_name]

            return result
        except Exception as e:
            eee(e)

    @staticmethod
    async def get_blog(request: Request):
        try:
            gv.request = request
            
            ConfigManager.load_data()
            
            page_config = PageRenderer.load_page_config('blog_config.yaml').copy()
            
            rendered_components = [
                PageRenderer.generate_html(component) for component in page_config['components']
            ]
            
            template = Template(gv.BASE_HTML)
            h = template.render(
                page_title=page_config['title'],
                components=rendered_components
            )
            
            return HTMLResponse(content=h)

        except Exception as e:
            eee(e)
    
    @staticmethod
    async def get_posts_form(request: Request):
        try:
            gv.request = request

            ConfigManager.load_data()

            query_params = dict(request.query_params)

            result = []

            if 'id' in query_params:

                id = int(query_params['id'])

                result = DatabaseManager.tm.execute_transactions(
                    transaction_name='get_post_detail',
                    params={
                        'id': id
                    },
                    config_file="cms.yaml"
                )
                result = [dict(row) for row in result]  # 转换为字典列表

                h = ''
                try:
                    if len(result) > 0:
                        PageRenderer.load_page_config('blog_config.yaml')
                        gv.component_dict['form_put']['data'] = result[0]

                        h = PageRenderer.generate_html(gv.component_dict['form_put'])
                except Exception as e:
                    eee(e)

                return HTMLResponse(content=h)

            else:

                h = ''
                try:
                    if True:
                        PageRenderer.load_page_config('blog_config.yaml')
                        gv.component_dict['form_post']['data'] = result
                        h = PageRenderer.generate_html(gv.component_dict['form_post'])
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
            
            ConfigManager.load_data()

            # 获取 URL 路径
            full_path = request.url.path

            # 去除末尾的斜杠，然后按 "/" 分割路径
            path_parts = full_path.rstrip("/").split("/")

            func_name = 'get' + '_'.join(path_parts)
            
            # 获取最后一个部分作为 page_name
            page_name = unquote(path_parts[-1]) if path_parts else ""
            
            query_params = BlogManager.get_query_paramas(request)
            query_params['data_name'] = page_name
            
            result = BlogManager.get_data(func_name, query_params)

            gv.component_dict[page_name]['data'] = result
            gv.component_dict[page_name]['query_params'] = query_params

            h = PageRenderer.generate_html(gv.component_dict[page_name])

            return HTMLResponse(content=h)

        except Exception as e:
            eee(e)

    @staticmethod
    async def post(request: Request):
        try:
            gv.request = request

            # 获取 URL 路径
            full_path = request.url.path

            # 去除末尾的斜杠，然后按 "/" 分割路径
            path_parts = full_path.rstrip("/").split("/")

            form_data = await request.form()
            
            func_name = 'post' + '_'.join(path_parts)

            result = DatabaseManager.tm.execute_transactions(
                transaction_name=func_name,
                params=form_data,
                config_file="cms.yaml"
            )

            headers = {"HX-Trigger": func_name}
            return HTMLResponse(content='ok', headers=headers)

        except Exception as e:
            eee(e)


    @staticmethod
    async def put(request: Request):
        try:
            gv.request = request

            # 获取 URL 路径
            full_path = request.url.path

            # 去除末尾的斜杠，然后按 "/" 分割路径
            path_parts = full_path.rstrip("/").split("/")

            form_data = await request.form()
            
            func_name = 'put' + '_'.join(path_parts)

            result = DatabaseManager.tm.execute_transactions(
                transaction_name=func_name,
                params=form_data,
                config_file="cms.yaml"
            )

            headers = {"HX-Trigger": func_name}
            return HTMLResponse(content='ok', headers=headers)

        except Exception as e:
            eee(e)
            
    @staticmethod
    async def delete(request: Request):
        try:
            gv.request = request

            # 获取 URL 路径
            full_path = request.url.path

            # 去除末尾的斜杠，然后按 "/" 分割路径
            path_parts = full_path.rstrip("/").split("/")

            func_name = 'delete' + '_'.join(path_parts)

            query_params = dict(request.query_params)

            result = DatabaseManager.tm.execute_transactions(
                transaction_name=func_name,
                params=query_params,
                config_file="cms.yaml"
            )

            headers = {"HX-Trigger": func_name}
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
            resolved_data = ConfigManager.resolve_inheritance(config, all_base_data)
                
            # 将 base_data 中不冲突的部分合并到最终结果中
            final_data = ConfigManager.deep_merge(gv.base_config, resolved_data)
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
    def generate_html(component: Dict[str, Any]) -> str:
        try:
            component = copy.deepcopy(component)

            if 'type' not in component:
                component['type'] = 'div'

            for key in ['config', 'data', 'value', 'files']:
                if key in component and isinstance(component[key], str):
                    if '.' in component[key]:
                        k = component[key].split('.')
                        if len(k) == 2:
                            # 获取类
                            cls = globals()[k[0]]
                            # 获取静态方法并调用
                            component[key] = getattr(cls, k[1])()
                    pass

            if 'cols' in component:
                
                for key in component['cols']:
                    if component['type'] == 'form_base_type_1':
                        config_id = component['config']['id'] + '_config'
                        if hasattr(gv, config_id):
                            pass
                        else:
                            setattr(gv, config_id, ConfigManager.get_table_config(component['config']['id']))
                  
                        config = getattr(gv, config_id)
                        if 'cols' in config and key in config['cols']:
                            component['cols'][key] = config['cols'][key] | component['cols'][key]
                        
                        if 'value' in component['cols'][key]:
                            value = component['cols'][key]['value']
                            if value and isinstance(value, str):
                                k = value.split('.')
                                if len(k) == 2:
                                    data = component.get('data', {})
                                    if len(data) == 1: 
                                        if k[1] in data[0]:
                                            component['cols'][key]['value'] = data[0][k[1]]

            template = Template(gv.HTML_TEMPLATES.get(component['type'], ''))
            rendered_children = {}
            
            if 'children' in component:
                if isinstance(component['children'], list):
                    rendered_children = []
                    for child in component.get('children', []):
                        child1 = PageRenderer.resolve_component(child)
                        child1['data'] = component.get('data', {})
                        rendered_children.append(PageRenderer.generate_html(child1))
                else:
                    for key, value in component['children'].items():
                        if isinstance(key, str):
                            if value:
                                rendered_children[key] = [PageRenderer.generate_html(PageRenderer.resolve_component(child)) for child in value]

            data = component.get('data', {})

            h = template.render(
                component=component,
                attributes=component.get('attributes', {}),
                config=component.get('config', {}),
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
                format_children=PageRenderer.format_children,
                query_params=component.get('query_params', {})
            )

            return h
        except Exception as e:
            eee(e)

    @staticmethod
    def format_attr(attributes, data = None, component = None):
        try:
            s = ''
            if attributes:
                for attr, value in attributes.items():
                    if attr == 'hx-get' or attr == 'hx-post' or attr == 'hx-put' or attr == 'hx-delete':
                        if value == 'history_back':
                            parsed_url = urlparse(gv.request.headers['hx-current-url'])
                            value = '{}?{}'.format(parsed_url.path, parsed_url.query)
                        else:
                            if data:
                                if isinstance(data, list) and len(data) == 1:
                                    data1 = data[0]
                                    value = BlogManager.get_formatted_url(value, data1)
                                else:
                                    value = BlogManager.get_formatted_url(value, data)
                            else:
                                query_params = BlogManager.get_query_paramas(gv.request)
                                if component:
                                    PRMS = component.get('const', {}).get('params', {})
                                    query_params = BlogManager.get_query_paramas(gv.request, PRMS.copy())
                                    PRMS = component.get('const', {}).get('params', {})
                                    
                                value = BlogManager.get_formatted_url(value, query_params)
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

            page_config = PageRenderer.load_page_config(page_name + '_config.yaml')

            rendered_components = [PageRenderer.generate_html(component) for component in page_config['components']]

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
