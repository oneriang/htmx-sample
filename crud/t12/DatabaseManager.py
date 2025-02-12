import os
import sys
import re
import uvicorn
import json
from pathlib import Path

import traceback

from sqlalchemy import create_engine, MetaData, Table, select, insert, update, delete, inspect, or_, and_, func, desc, asc
from sqlalchemy.orm import sessionmaker, class_mapper
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.sql import expression
from sqlalchemy.sql.sqltypes import String, Integer, DateTime, Date, Boolean, Enum
from sqlalchemy import inspect, String, Integer, Float, DateTime, Date, Boolean, Enum

from transaction_module import convert_value, TransactionModule

from fastapi import FastAPI, Response, Request, Form, Depends, HTTPException, status

import gv as gv

from ConfigManager import ConfigManager

class DatabaseManager:
    """数据库管理类，处理数据库连接和操作"""
    DATABASE_URL = "sqlite:///./cms.db"
    engine = create_engine(DATABASE_URL)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    metadata = MetaData()
    metadata.reflect(bind=engine, views=True)

    db = SessionLocal()
    tm = TransactionModule(
        engine=engine, db=db, metadata=metadata)

    @staticmethod
    def get_table_names():
        try:
            inspector = inspect(DatabaseManager.engine)
            return inspector.get_table_names()

        except Exception as e:
            # 例外情報を取得
            exc_type, exc_value, exc_traceback = sys.exc_info()
            # 行番号を取得
            line_number = traceback.extract_tb(exc_traceback)[-1].lineno
            print(f"例外の型: {exc_type.__name__}, 行番号: {line_number}")
            return None

    @staticmethod
    def get_view_names():
        try:
            inspector = inspect(DatabaseManager.engine)
            return inspector.get_view_names()

        except Exception as e:
            # 例外情報を取得
            exc_type, exc_value, exc_traceback = sys.exc_info()
            # 行番号を取得
            line_number = traceback.extract_tb(exc_traceback)[-1].lineno
            print(f"例外の型: {exc_type.__name__}, 行番号: {line_number}")
            return None

    @staticmethod
    def get_tables():
        try:
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

        except Exception as e:
            # 例外情報を取得
            exc_type, exc_value, exc_traceback = sys.exc_info()
            # 行番号を取得
            line_number = traceback.extract_tb(exc_traceback)[-1].lineno
            print(f"例外の型: {exc_type.__name__}, 行番号: {line_number}")
            return None

    @staticmethod
    def generate_table_or_view_config(engine, name, is_view=False):
        try:
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
                    # Views might not have this information
                    "nullable": column.get('nullable', True),
                    # Views might not have this information
                    "primary_key": column.get('primary_key', False)
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

        except Exception as e:
            # 例外情報を取得
            exc_type, exc_value, exc_traceback = sys.exc_info()
            # 行番号を取得
            line_number = traceback.extract_tb(exc_traceback)[-1].lineno
            print(f"例外の型: {exc_type.__name__}, 行番号: {line_number}")
            return None

    # Generate configurations for all tables and views
    @staticmethod
    def generate_all_configs(engine):
        try:
            inspector = inspect(engine)

            # Generate config for tables
            for table_name in inspector.get_table_names():
                DatabaseManager.generate_table_or_view_config(
                    engine, table_name)

            # Generate config for views
            for view_name in inspector.get_view_names():
                DatabaseManager.generate_table_or_view_config(
                    engine, view_name, is_view=True)

        except Exception as e:
            # 例外情報を取得
            exc_type, exc_value, exc_traceback = sys.exc_info()
            # 行番号を取得
            line_number = traceback.extract_tb(exc_traceback)[-1].lineno
            print(f"例外の型: {exc_type.__name__}, 行番号: {line_number}")
            return None

    @staticmethod
    def apply_search_filter(query, table, column_config, value, is_keyword_search=False):
        try:
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

        except Exception as e:
            # 例外情報を取得
            exc_type, exc_value, exc_traceback = sys.exc_info()
            # 行番号を取得
            line_number = traceback.extract_tb(exc_traceback)[-1].lineno
            print(f"例外の型: {exc_type.__name__}, 行番号: {line_number}")
            return None

    @staticmethod
    def get_table_data(
        request: Request = None,
        table_name: str = None,
        page: int = 1,
        page_size: int = 5,
        sort_column: str | None = None,
        sort_direction: str = 'asc'
    ):
        try:
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
            if table_name in DatabaseManager.metadata.tables:
                table = DatabaseManager.metadata.tables[table_name]
            if table is None:
                raise HTTPException(status_code=404, detail="Table not found")

            table_config = ConfigManager.get_table_config(table_name)

            # Get primary key and calculate offset for pagination
            # 获取主键并计算分页的偏移量
            primary_key = next(
                (col['name'] for col in table_config['columns'] if col.get('primary_key')), None)
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
                        query = DatabaseManager.apply_search_filter(
                            query, table, column_config, search_params[column_config['name']])

            # Apply sorting if a sort column is specified
            # 如果指定了排序列，应用排序
            if sort_column and sort_column in table.columns:
                sort_func = desc if sort_direction.lower() == 'desc' else asc
                query = query.order_by(
                    sort_func(getattr(table.c, sort_column)))

            with DatabaseManager.SessionLocal() as session:
                # Get total count and paginated results
                # 获取总数和分页结果
                count_query = select(func.count()).select_from(query.alias())
                total_items = session.execute(count_query).scalar()
                result = session.execute(query.offset(
                    offset).limit(page_size)).fetchall()

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

        except Exception as e:
            # 例外情報を取得
            exc_type, exc_value, exc_traceback = sys.exc_info()
            # 行番号を取得
            line_number = traceback.extract_tb(exc_traceback)[-1].lineno
            print(f"例外の型: {exc_type.__name__}, 行番号: {line_number}")
            return None
