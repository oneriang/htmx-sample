import os
import sys
import re
import uvicorn
import json
from pathlib import Path

import traceback

from typing import Dict, Any, List, Union, Optional

import yaml

import gv as gv

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

        except Exception as e:
            eee(e)

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

        except Exception as e:
            eee(e)

    @staticmethod
    def load_data():
        try:
            if gv.BASE_HTML:
                pass
            else:
                gv.BASE_HTML = ConfigManager.load_data_from_html(
                    'base_html.html')

            if False: #gv.HTML_TEMPLATES:
                pass
            else:
                gv.HTML_TEMPLATES = ConfigManager.load_data_from_yaml(
                    'html_templates.yaml')

            if gv.YAML_CONFIG:
                pass
            else:
                gv.YAML_CONFIG = ConfigManager.load_data_from_yaml(
                    'main_config.yaml')

            if gv.icons:
                pass
            else:
                gv.icons = gv.HTML_TEMPLATES.get('icons', {})

            if gv.classes:
                pass
            else:
                gv.classes = gv.HTML_TEMPLATES.get('classes', {})

            # 加载嵌入的 YAML 数据
            gv.base_config = ConfigManager.load_data_from_yaml('base_config.yaml')
            # pprint.pprint(gv.base_config)
            # child_config = yaml.safe_load(child_yaml)
            '''    
            # 合并所有基础数据
            all_base_config = deep_merge(base_config, child_config)
        
            # 解析继承关系
            resolved_config = resolve_inheritance(child_config, all_base_config)
        
            # 将 base_config 中不冲突的部分合并到最终结果中
            final_config = deep_merge(base_config, resolved_config)
            '''

        except Exception as e:
            eee(e)
            # # 例外情報を取得
            # exc_type, exc_value, exc_traceback = sys.exc_info()
            # # 行番号を取得
            # line_number = traceback.extract_tb(exc_traceback)[-1].lineno
            # print(f"例外の型: {exc_type.__name__}, 行番号: {line_number}")
            # return None

    @staticmethod
    def get_table_config(table_name=None):
        try:
            request = None

            if hasattr(gv, 'request'):
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

        except Exception as e:
            eee(e)

    @staticmethod
    def get_primary_key(table):
        try:
            return next(iter(table.primary_key.columns)).name
        except Exception as e:
            return None

        except Exception as e:
            eee(e)

    @staticmethod
    def get_column_type(column_type):
        try:
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

        except Exception as e:
            eee(e)

    @staticmethod
    def get_configs():
        return ConfigManager.get_table_config()

    @staticmethod
    def deep_merge(base, child):
        try:
            """
            递归合并两个字典，支持深层合并。
            如果字段冲突，优先使用 child 的值。
            """
            if isinstance(base, dict) and isinstance(child, dict):
                merged = base.copy()  # 复制 base 数据
                for key, value in child.items():
                    if key in merged and isinstance(merged[key], dict) and isinstance(value, dict):
                        # 如果键存在且值是字典，则递归合并
                        merged[key] = ConfigManager.deep_merge(
                            merged[key], value)
                    else:
                        # 否则直接使用 child 的值
                        merged[key] = value
                return merged
            else:
                # 如果 base 或 child 不是字典，则直接使用 child 的值
                return child
        except Exception as e:
            eee(e)

    @staticmethod
    def resolve_inheritance(data, base_data):
        try:
            """
            递归解析继承关系，支持 base 属性。
            """
            if isinstance(data, dict):
                # 如果存在 base 属性，则进行继承
                if 'base' in data:
                    base_key = data.pop('base')  # 删除 base 键
                    # 递归查找 base 数据
                    base_value = ConfigManager.get_nested_value(
                        base_data, base_key)
                    if base_value is not None:
                        # 递归解析 base 数据
                        base_value = ConfigManager.resolve_inheritance(
                            base_value, base_data)
                        # 深层合并 base 数据和当前数据
                        data = ConfigManager.deep_merge(base_value, data)
                    else:
                        raise ValueError(
                            f"Base key '{base_key}' not found in base data.")

                # 递归处理所有子属性
                for key, value in data.items():
                    data[key] = ConfigManager.resolve_inheritance(
                        value, base_data)

            elif isinstance(data, list):
                # 如果是列表，递归处理每个元素
                data = [ConfigManager.resolve_inheritance(
                    item, base_data) for item in data]

            return data

        except Exception as e:
            eee(e)

    @staticmethod
    def get_nested_value(data, key_path):
        try:
            """
            根据点分隔的路径（如 'component_definitions.modal_form'）获取嵌套字典中的值。
            """
            keys = key_path.split('.')
            current = data
            for key in keys:
                if isinstance(current, dict) and key in current:
                    current = current[key]
                else:
                    return None
            return current

        except Exception as e:
            eee(e)
