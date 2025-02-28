import uvicorn
import sys
import shutil
import os
import re
import shutil
import os
import magic
import sqlite3

from typing import List, Dict, Any, Union, Optional
from datetime import datetime, date, time, timedelta

from fastapi import FastAPI, Depends, HTTPException, Response, Form
from fastapi import UploadFile, File
from fastapi.responses import FileResponse
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

from sqlalchemy import (
    create_engine, MetaData, inspect, text, Table, Column, select, and_, or_,
    Integer, String, Float, DateTime, Date, Boolean, ForeignKey,
    Text, DECIMAL, BLOB, Time, Interval, SmallInteger, BigInteger,
    Unicode, UnicodeText, LargeBinary, Numeric, func, asc, desc
)

from sqlalchemy.sql import func
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.exc import OperationalError, ProgrammingError
from sqlalchemy.engine.url import URL, make_url
from sqlalchemy.types import TypeEngine

import yaml
import logging
import traceback

import gv as gv

# Set up logging
logging.basicConfig(level=logging.CRITICAL)
logger = logging.getLogger(__name__)
#logging.getLogger('sqlalchemy.engine').setLevel(logging.DEBUG)


def convert_value(column_type: Any, value: Any) -> Any:
    if value == 'None' or value is None:
        return None
    # print(column_type)
    # print(value)
    if isinstance(column_type, BLOB):
        if isinstance(value, str):
            return value.encode('utf-8')
        elif isinstance(value, bytes):
            return value
        else:
            raise ValueError(f"无法将 {type(value)} 转换为 BLOB 类型")

    elif isinstance(column_type, Date):
        
        if isinstance(value, str):
            #print(value)
            # 尝试多种日期格式
            for fmt in ('%Y-%m-%d', '%d-%m-%Y', '%Y/%m/%d', '%d/%m/%Y'):
                try:
                    return datetime.strptime(value, fmt).date()
                except ValueError:
                    continue
            raise ValueError(f"无法将字符串 '{value}' 解析为日期")
        elif isinstance(value, datetime):
            return value.date()
        elif isinstance(value, date):
            return value
        else:
            raise ValueError(f"无法将 {type(value)} 转换为日期类型")

    elif isinstance(column_type, Time):
        if isinstance(value, str):
            # 尝试多种时间格式
            for fmt in ('%H:%M:%S', '%H:%M', '%I:%M:%S %p', '%I:%M %p'):
                try:
                    return datetime.strptime(value, fmt).time()
                except ValueError:
                    continue
            raise ValueError(f"无法将字符串 '{value}' 解析为时间")
        elif isinstance(value, datetime):
            return value.time()
        elif isinstance(value, time):
            return value
        else:
            raise ValueError(f"无法将 {type(value)} 转换为时间类型")

    elif isinstance(column_type, DateTime):
        if isinstance(value, str):
            # 尝试多种日期时间格式
            for fmt in ('%Y-%m-%d', '%d-%m-%Y', '%Y/%m/%d', '%d/%m/%Y', '%Y-%m-%d %H:%M:%S', '%d-%m-%Y %H:%M:%S', '%Y-%m-%d %H:%M', '%d-%m-%Y %H:%M'):
                try:
                    return datetime.strptime(value, fmt)
                except ValueError:
                    continue
            raise ValueError(f"无法将字符串 '{value}' 解析为日期时间")
        elif isinstance(value, (date, time)):
            return datetime.combine(value if isinstance(value, date) else date.today(),
                                    value if isinstance(value, time) else time())
        elif isinstance(value, datetime):
            return value
        else:
            raise ValueError(f"无法将 {type(value)} 转换为日期时间类型")

    elif isinstance(column_type, Interval):
        if isinstance(value, str):
            # 解析如 "3 days 2 hours 1 minute" 的字符串
            parts = re.findall(r'(\d+)\s*(\w+)', value)
            delta = timedelta()
            for number, unit in parts:
                number = int(number)
                if 'day' in unit:
                    delta += timedelta(days=number)
                elif 'hour' in unit:
                    delta += timedelta(hours=number)
                elif 'minute' in unit:
                    delta += timedelta(minutes=number)
                elif 'second' in unit:
                    delta += timedelta(seconds=number)
            return delta
        elif isinstance(value, (timedelta, int, float)):
            return timedelta(seconds=value) if isinstance(value, (int, float)) else value
        else:
            raise ValueError(f"无法将 {type(value)} 转换为间隔类型")

    else:
        # 对于其他类型，尝试直接转换
        python_type = column_type.python_type
        try:
            return python_type(value)
        except ValueError:
            return value

class TransactionError(Exception):
    """自定义事务错误类"""
    def __init__(self, message: str, step: Optional[Dict[str, Any]] = None, 
                original_error: Optional[Exception] = None):
        self.message = message
        self.step = step
        self.original_error = original_error
        self.traceback = traceback.extract_tb(sys.exc_info()[2])
        super().__init__(self.message)

class Transaction:
    def __init__(self, name: str, steps: List[Dict[str, Any]]):
        self.name = name
        self.steps = steps

gv.data = {}

class TransactionModule:

    def __init__(self, database_url = None, engine = None, db = None, metadata = None):

        if engine and db and metadata:
            self.engine = engine
            self.db = db
            self.metadata = metadata
        else:
            if database_url:
                # DATABASE_URL = "sqlite:///./" + database_url
                self.engine = create_engine(database_url)   
            elif engine:
                self.engine = engine
            else:
                return None

            self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
            self.db = self.SessionLocal()
            self.metadata = MetaData()
            self.metadata.create_all(bind=self.engine)

        pass

    dynamic_values = {
        'current_timestamp': datetime.now(),
        'current_date': date.today(),
        'current_time': datetime.now().time(),
        'yesterday': date.today() - timedelta(days=1),
        'tomorrow': date.today() + timedelta(days=1),
        'year': date.today().year,
        'month': date.today().month,
        'day': date.today().day,
        'week_start': date.today() - timedelta(days=date.today().weekday()),
        'week_end': date.today() + timedelta(days=6-date.today().weekday()),
        'month_start': date.today().replace(day=1),
        'month_end': (date.today().replace(day=1) + timedelta(days=32)).replace(day=1) - timedelta(days=1),
        'year_start': date.today().replace(month=1, day=1),
        'year_end': date.today().replace(month=12, day=31),
    }

    def format_error_location(self, tb_frames) -> str:
        """格式化错误位置信息"""
        error_locations = []
        for frame in tb_frames:
            error_locations.append(f"  File '{frame.filename}', line {frame.lineno}, in {frame.name}\n    {frame.line}")
        return "\n".join(error_locations)
        
    def process_dynamic_params(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """处理动态参数，替换特殊标记为实际值"""
        def replace_value(value: Any) -> Any:
            if isinstance(value, str):
                # 检查是否包含动态参数标记
                match = re.match(r'{{\s*([^}]+)\s*}}', value)
                if match:
                    param_name = match.group(1).strip()
                    if param_name in self.dynamic_values:
                        return self.dynamic_values[param_name]
            return value

        def process_dict(d: Dict[str, Any]) -> Dict[str, Any]:
            result = {}
            for k, v in d.items():
                if isinstance(v, dict):
                    result[k] = process_dict(v)
                elif isinstance(v, list):
                    result[k] = process_list(v)
                else:
                    result[k] = replace_value(v)
            return result

        def process_list(l: List[Any]) -> List[Any]:
            return [process_dict(x) if isinstance(x, dict) else 
                    process_list(x) if isinstance(x, list) else 
                    replace_value(x) for x in l]

        return process_dict(params) if params else {}

    def get_column_type(self, type_name: str, length: Optional[int] = None, 
                    precision: Optional[int] = None, scale: Optional[int] = None) -> TypeEngine:
        """Convert string type names to SQLAlchemy types"""
        type_map = {
            'integer': Integer,
            'bigint': BigInteger,
            'smallint': SmallInteger,
            'string': lambda length: String(length) if length else String,
            'unicode': lambda length: Unicode(length) if length else Unicode,
            'float': Float,
            'numeric': lambda p, s: Numeric(precision=p, scale=s) if p and s else Numeric,
            'decimal': lambda p, s: DECIMAL(precision=p, scale=s) if p and s else DECIMAL,
            'datetime': DateTime,
            'date': Date,
            'time': Time,
            'boolean': Boolean,
            'text': Text,
            'unicodetext': UnicodeText,
            'blob': LargeBinary,
            'binary': LargeBinary,
            'interval': Interval
        }
        
        type_name = type_name.lower()
        if type_name not in type_map:
            raise ValueError(f"Unsupported column type: {type_name}")
            
        if type_name in ['string', 'unicode']:
            return type_map[type_name](length)
        elif type_name in ['numeric', 'decimal']:
            return type_map[type_name](precision, scale)
        else:
            return type_map[type_name]()

    # 定义允许的文件类型和最大文件大小
    ALLOWED_EXTENSIONS = {'.txt', '.pdf', '.png', '.jpg', '.jpeg', '.gif'}
    MAX_FILE_SIZE = 5 * 1024 * 1024  # 5 MB

    def allowed_file(self, filename: str) -> bool:
        return os.path.splitext(filename)[1].lower() in self.ALLOWED_EXTENSIONS

    def validate_file_type(self, file: UploadFile) -> bool:
        mime = magic.Magic(mime=True)
        file_type = mime.from_buffer(file.file.read(1024))
        file.file.seek(0)  # Reset file pointer
        return file_type.split('/')[1] in [ext.lstrip('.') for ext in self.ALLOWED_EXTENSIONS]

    def validate_file_size(self, file: UploadFile) -> bool:
        file.file.seek(0, 2)  # Move to the end of the file
        file_size = file.file.tell()  # Get the position (size)
        file.file.seek(0)  # Reset file pointer
        return file_size <= self.MAX_FILE_SIZE

    def create_database(self, step: Dict[str, Any]) -> Dict[str, Any]:
        """创建新数据库"""
        db_name = step.get("database_name")
        if not db_name:
            raise ValueError("Database name is required")
        
        # SQLite 特定的处理
        if db_name.endswith('.db'):
            db_path = os.path.abspath(db_name)
            try:
                # 创建新的 SQLite 数据库
                conn = sqlite3.connect(db_path)
                
                # 如果提供了初始 SQL，执行它
                if "init_sql" in step:
                    cursor = conn.cursor()
                    cursor.executescript(step["init_sql"])
                    conn.commit()
                    
                conn.close()
                return {
                    "message": f"Database {db_name} created successfully",
                    "path": db_path
                }
            except Exception as e:
                raise Exception(f"Failed to create database {db_name}: {str(e)}")
        else:
            raise ValueError("Only .db extension is supported for SQLite databases")

    def alter_table(self, step: Dict[str, Any]) -> Dict[str, Any]:
        """修改表结构"""
        table = step["table"]
        operation = step["operation"]
        
        try:
            if operation == "add_column":
                for col in step["columns"]:
                    # 构建 ALTER TABLE 语句
                    col_type = self.get_column_type(
                        col["type"], 
                        col.get("length"),
                        col.get("precision"),
                        col.get("scale")
                    )
                    nullable_str = "" if col.get("nullable", True) else "NOT NULL"
                    default_str = f"DEFAULT {col['default']}" if "default" in col else ""
                    
                    # 转换 SQLAlchemy 类型为 SQLite 类型字符串
                    type_str = str(col_type.compile(dialect=self.db.bind.dialect))
                    
                    sql = f"""
                    ALTER TABLE {table} 
                    ADD COLUMN {col['name']} {type_str} {nullable_str} {default_str}
                    """
                    self.db.execute(text(sql))
                    
            elif operation == "drop_column":
                # 获取当前表的所有列
                inspector = inspect(self.db.get_bind())
                columns = [col['name'] for col in inspector.get_columns(table)]
                
                # 移除要删除的列
                remaining_columns = [col for col in columns if col not in step["columns"]]
                
                # 创建新表
                col_list = ", ".join(remaining_columns)
                new_table = f"{table}_new"
                
                # 复制数据到新表
                sql = f"""
                CREATE TABLE {new_table} AS 
                SELECT {col_list} 
                FROM {table}
                """
                self.db.execute(text(sql))
                
                # 删除旧表并重命名新表
                self.db.execute(text(f"DROP TABLE {table}"))
                self.db.execute(text(f"ALTER TABLE {new_table} RENAME TO {table}"))
                
            elif operation == "modify_column":
                # 获取当前表的所有列信息
                inspector = inspect(self.db.get_bind())
                columns = inspector.get_columns(table)
                
                # 准备新表的列定义
                new_columns = []
                for col in columns:
                    if col['name'] in [mod_col['name'] for mod_col in step['columns']]:
                        # 使用新的列定义
                        mod_col = next(mc for mc in step['columns'] if mc['name'] == col['name'])
                        col_type = self.get_column_type(
                            mod_col["type"],
                            mod_col.get("length"),
                            mod_col.get("precision"),
                            mod_col.get("scale")
                        )
                        type_str = str(col_type.compile(dialect=self.db.bind.dialect))
                        nullable_str = "" if mod_col.get("nullable", True) else "NOT NULL"
                        new_columns.append(f"{col['name']} {type_str} {nullable_str}")
                    else:
                        # 保持原有列定义
                        type_str = str(col['type'].compile(dialect=self.db.bind.dialect))
                        nullable_str = "" if col.get("nullable", True) else "NOT NULL"
                        new_columns.append(f"{col['name']} {type_str} {nullable_str}")
                
                # 创建新表
                col_def = ", ".join(new_columns)
                new_table = f"{table}_new"
                
                sql = f"""
                CREATE TABLE {new_table} (
                    {col_def}
                )
                """
                self.db.execute(text(sql))
                
                # 复制数据
                col_list = ", ".join(col['name'] for col in columns)
                self.db.execute(text(f"""
                    INSERT INTO {new_table}
                    SELECT {col_list}
                    FROM {table}
                """))
                
                # 删除旧表并重命名新表
                self.db.execute(text(f"DROP TABLE {table}"))
                self.db.execute(text(f"ALTER TABLE {new_table} RENAME TO {table}"))
            
            self.db.commit()
            return {"message": f"Table {table} altered successfully"}
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to alter table {table}: {str(e)}")
            raise Exception(f"Failed to alter table {table}: {str(e)}")

    def drop_database(self, step: Dict[str, Any]) -> Dict[str, Any]:
        """删除数据库"""
        db_name = step.get("database_name")
        if not db_name:
            raise ValueError("Database name is required")
        
        # SQLite 特定的处理
        if db_name.endswith('.db'):
            db_path = os.path.abspath(db_name)
            try:
                if os.path.exists(db_path):
                    os.remove(db_path)
                    return {"message": f"Database {db_name} dropped successfully"}
                else:
                    raise FileNotFoundError(f"Database {db_name} does not exist")
            except Exception as e:
                raise Exception(f"Failed to drop database {db_name}: {str(e)}")
        else:
            raise ValueError("Only .db extension is supported for SQLite databases")

    def backup_database(self, step: Dict[str, Any]) -> Dict[str, Any]:
        """备份数据库"""
        db_name = step.get("database_name")
        backup_path = step.get("backup_path")
        if not db_name or not backup_path:
            raise ValueError("Both database_name and backup_path are required")
        
        # SQLite 特定的处理
        if db_name.endswith('.db'):
            db_path = os.path.abspath(db_name)
            try:
                if os.path.exists(db_path):
                    # 确保备份目录存在
                    os.makedirs(os.path.dirname(backup_path), exist_ok=True)
                    # 复制数据库文件
                    shutil.copy2(db_path, backup_path)
                    return {
                        "message": f"Database {db_name} backed up successfully",
                        "backup_path": backup_path
                    }
                else:
                    raise FileNotFoundError(f"Database {db_name} does not exist")
            except Exception as e:
                raise Exception(f"Failed to backup database {db_name}: {str(e)}")
        else:
            raise ValueError("Only .db extension is supported for SQLite databases")

    def restore_database(self, step: Dict[str, Any]) -> Dict[str, Any]:
        """从备份恢复数据库"""
        backup_path = step.get("backup_path")
        db_name = step.get("database_name")
        if not backup_path or not db_name:
            raise ValueError("Both backup_path and database_name are required")
        
        # SQLite 特定的处理
        if db_name.endswith('.db'):
            db_path = os.path.abspath(db_name)
            try:
                if os.path.exists(backup_path):
                    # 如果目标数据库存在，先删除
                    if os.path.exists(db_path):
                        os.remove(db_path)
                    # 复制备份文件到目标位置
                    shutil.copy2(backup_path, db_path)
                    return {
                        "message": f"Database {db_name} restored successfully",
                        "path": db_path
                    }
                else:
                    raise FileNotFoundError(f"Backup file {backup_path} does not exist")
            except Exception as e:
                raise Exception(f"Failed to restore database {db_name}: {str(e)}")
        else:
            raise ValueError("Only .db extension is supported for SQLite databases")

    def list_databases(self, step: Dict[str, Any]) -> Dict[str, Any]:
        """列出指定目录下的所有数据库"""
        directory = step.get("directory", ".")
        try:
            # 获取指定目录下的所有.db文件
            databases = []
            for file in os.listdir(directory):
                if file.endswith('.db'):
                    db_path = os.path.join(directory, file)
                    db_size = os.path.getsize(db_path)
                    db_modified = os.path.getmtime(db_path)
                    databases.append({
                        "name": file,
                        "path": db_path,
                        "size": db_size,
                        "modified": db_modified
                    })
            return {"databases": databases}
        except Exception as e:
            raise Exception(f"Failed to list databases: {str(e)}")

    def get_database_info(self, step: Dict[str, Any]) -> Dict[str, Any]:
        """获取数据库详细信息"""
        db_name = step.get("database_name")
        if not db_name:
            raise ValueError("Database name is required")
        
        # SQLite 特定的处理
        if db_name.endswith('.db'):
            db_path = os.path.abspath(db_name)
            try:
                if not os.path.exists(db_path):
                    raise FileNotFoundError(f"Database {db_name} does not exist")
                
                # 创建临时连接以获取数据库信息
                conn = sqlite3.connect(db_path)
                cursor = conn.cursor()
                
                # 获取表列表及其结构
                tables = []
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
                for table_row in cursor.fetchall():
                    table = table_row[0]
                    cursor.execute(f"PRAGMA table_info({table})")
                    columns = []
                    for col in cursor.fetchall():
                        columns.append({
                            "name": col[1],
                            "type": col[2],
                            "nullable": not col[3],
                            "primary_key": bool(col[5])
                        })
                    
                    # 获取表的行数
                    cursor.execute(f"SELECT COUNT(*) FROM {table}")
                    row_count = cursor.fetchone()[0]
                    
                    tables.append({
                        "name": table,
                        "columns": columns,
                        "row_count": row_count
                    })
                
                # 获取数据库大小和其他元数据
                db_size = os.path.getsize(db_path)
                db_modified = os.path.getmtime(db_path)
                
                conn.close()
                
                return {
                    "database": db_name,
                    "path": db_path,
                    "size": db_size,
                    "modified": db_modified,
                    "tables": tables
                }
                
            except Exception as e:
                raise Exception(f"Failed to get database info for {db_name}: {str(e)}")
        else:
            raise ValueError("Only .db extension is supported for SQLite databases")

    def execute_step(self, step: Dict[str, Any]) -> Any:
        # print('execute_step1')
        """执行单个步骤，包含增强的错误处理"""
        try:
            # 记录开始执行的步骤
            #logger.info(f"Executing step: {step.get('action', 'unknown')} "
            #        f"on table: {step.get('table', 'unknown')}")
            
            action = step["action"]
            #print(action)
            if action != "create_table" and 'table' in step:
                table = Table(step["table"], self.metadata, autoload_with=self.engine)
                
            #print(action)
            
            try:
                
                # 处理步骤中的动态参数
                step = self.process_dynamic_params(step)
                # print(step)
        
                # 添加新的表管理操作
                if action == "create_table":
                    table = step["table"]
                    columns = []
                    
                    for col in step["columns"]:
                        col_type = self.get_column_type(
                            col["type"], 
                            col.get("length"), 
                            col.get("precision"), 
                            col.get("scale")
                        )
                        
                        column_args = {
                            "primary_key": col.get("primary_key", False),
                            "nullable": col.get("nullable", True),
                        }
                        
                        # 处理外键
                        if "foreign_key" in col:
                            fk_ref = col["foreign_key"]
                            column_args["foreign_key"] = ForeignKey(
                                f"{fk_ref['table']}.{fk_ref['column']}"
                            )
                        
                        # 处理默认值
                        if "default" in col:
                            column_args["default"] = col["default"]
                        
                        columns.append(Column(
                            col["name"],
                            col_type,
                            **column_args
                        ))
                    
                    # 创建表
                    new_table = Table(table, self.metadata, *columns)
                    new_table.create(self.engine, checkfirst=True)
                    return {"message": f"Table {table} created successfully"}
        
                elif action == "drop_table":
                    table = step["table"]
                    table = Table(table, self.metadata)
                    table.drop(self.engine, checkfirst=True)
                    return {"message": f"Table {table} dropped successfully"}
        
                # 添加数据库级别的操作
                elif action == "create_database":
                    return self.create_database(step)
                elif action == "drop_database":
                    return self.drop_database(step)
                elif action == "backup_database":
                    return self.backup_database(step)
                elif action == "restore_database":
                    return self.restore_database(step)
                elif action == "list_databases":
                    return self.list_databases(step)
                elif action == "database_info":
                    return self.get_database_info(step)
                elif action == "alter_table":
                    return self.alter_table(step)
                elif action == "insert":
                    print('insert')
                    #(gv.data[step.get('data_from')])
                    result = self.db.execute(table.insert().values(**step["values"]))
                    return result.rowcount
                elif action == "update":
                    print('update')
                    #print(gv.data[step.get('data_from')])
                    filters = self.build_filter_clauses(step.get("filter_values", []), table)
                    result = self.db.execute(table.update().where(*filters).values(**step["values"]))
                    return result.rowcount
                elif action == "delete":
                    filters = self.build_filter_clauses(step.get("filter_values", []), table)
                    result = self.db.execute(table.delete().where(*filters))
                    return result.rowcount
                elif action == "get4":
                    query = self.build_query(step, table)
                    result = self.db.execute(query).mappings().all()
                    # print('±+++++(+++++(((+++')
                    # print(result)
                    if step.get('data_to'):
                        gv.data[step.get('data_to')] = result
                    return result
                elif action == "get":
                    logger.info("\nBuilding and executing query...")
                    query = self.build_query(step, table)
                    
                    try:
                        result = self.db.execute(query).mappings().all()
                        logger.info(f"\nQuery returned {len(result)} rows")
                        if len(result) > 0:
                            logger.info("First row sample:")
                            logger.info(dict(result[0]))
                        
                        if step.get('data_to'):
                            gv.data[step.get('data_to')] = result
                            logger.info(f"\nStored result in data_to: {step.get('data_to')}")
                        
                        return result
                        
                    except Exception as e:
                        logger.error(f"Error executing query: {str(e)}")
                        raise
                
                elif action == "get2":
                    query = select([table])
                    if "filter_values" in step:
                        filters = self.build_filter_clauses(step["filter_values"], table)
                        query = query.where(*filters)
                    if "fields" in step:
                        columns = [table.c[field] for field in step["fields"]]
                        query = query.with_only_columns(*columns)
                    result = self.db.execute(query).fetchall()
                    if step.get('data_to'):
                        gv.data[step.get('data_to')] = result
                    return result
                if action == "get3":
                    if "fields" in step:
                        columns = [table.c[field] for field in step["fields"]]
                        query = select(*columns)
                    else:
                        query = select(table)
        
                    if "filter_values" in step:
                        filters = self.build_filter_clauses(step["filter_values"], table)
                        query = query.where(*filters)
        
                    result = self.db.execute(query).fetchall()
                    '''
                    if step.get('data_to'):
                        gv.data[step.get('data_to')] = result
                    '''
                    return result
                elif action == "file_create":
                    try:
                        with open(step.get('file_name'), "w", encoding='utf-8') as file:
                            return file.write("\n".join([str(_) for _ in gv.data[step.get('data_from')]]))
                    except Exception as e:
                        logger.error(f"{e}")
                        return {}
                    return result
                elif action == "execute":
                    sql = step.get("sql")
                    '''
                    print('~`````````')
                    print(sql)
                    print('~`````````')
                    '''
                    if sql:
                        result = self.db.execute(text(sql))
                        return result.rowcount
                    else:
                        return None
                        #raise ValueError("SQL statement is missing for execute action")
                # elif action == "upload_file":
                #     file: UploadFile = step.get("file")
                #     destination: str = step.get("destination", "")
                #     if not file:
                #         raise ValueError("No file provided for upload")
                #     if not destination:
                #         raise ValueError("No destination provided for file upload")
                #     os.makedirs(os.path.dirname(destination), exist_ok=True)
                #     with open(destination, "wb") as buffer:
                #         shutil.copyfileobj(file.file, buffer)
                #     return {"filename": file.filename, "destination": destination}
                # elif action == "download_file":
                #     file_path: str = step.get("file_path", "")
                #     if not file_path or not os.path.exists(file_path):
                #         raise ValueError(f"File not found: {file_path}")
                #     return FileResponse(file_path, filename=os.path.basename(file_path))
                elif action == "upload_file":
                    print('upload_file')
                    file: UploadFile = step.get("file")
                    destination: str = step.get("folder_path", "") + '/' + step.get("file_name", "")
                    #print(file)
                    #print(destination)
                    if not file:
                        raise ValueError("No file provided for upload")
                    if not destination:
                        raise ValueError("No destination provided for file upload")
                    
                    # 文件类型验证
                    if not self.allowed_file(file.filename):
                        raise ValueError(f"File type not allowed. Allowed types are: {', '.join(self.ALLOWED_EXTENSIONS)}")
                    
                    # # 文件内容类型验证
                    # if not self.validate_file_type(file):
                    #     raise ValueError("File content does not match the allowed types")
                    
                    # 文件大小验证
                    if not self.validate_file_size(file):
                        raise ValueError(f"File size exceeds the maximum limit of {self.MAX_FILE_SIZE / (1024 * 1024)} MB")
                    
                    os.makedirs(os.path.dirname(destination), exist_ok=True)
                    with open(destination, "wb") as buffer:
                        shutil.copyfileobj(file.file, buffer)

                    print(destination)
                    return destination
                        
                    #print(file)
                    
                    # res = {"filename": file.filename, "destination": destination}
                    # '''
                    # print(res)
                    # '''
                    
                    # if step.get('data_to'):
                    #     gv.data[step.get('data_to')] = res
                    #     '''
                    #     print(step.get('data_to'))
                    #     print(gv.data[step.get('data_to')])
                    #     '''
                        
                    # return res
        
                elif action == "download_file":
                    file_path: str = step.get("file_path", "")
                    if not file_path or not os.path.exists(file_path):
                        raise ValueError(f"File not found: {file_path}")
                    
                    # 验证文件类型（可选，取决于您的需求）
                    if not self.allowed_file(file_path):
                        raise ValueError(f"File type not allowed for download. Allowed types are: {', '.join(self.ALLOWED_EXTENSIONS)}")
                    
                    return FileResponse(file_path, filename=os.path.basename(file_path))
                else:
                    raise ValueError(f"不支持的操作: {action}")
            except Exception as e:
                print(str(e))
                # 获取详细的错误信息
                exc_type, exc_value, exc_traceback = sys.exc_info()
                tb_frames = traceback.extract_tb(exc_traceback)
                
                error_msg = (
                    f"\nError executing step: {action}\n"
                    f"Step details: {step}\n"
                    f"Error type: {exc_type.__name__}\n"
                    f"Error message: {str(e)}\n"
                    f"Error location:\n{self.format_error_location(tb_frames)}"
                )
                
                logger.error(error_msg)
                raise TransactionError(
                    message=f"Step execution failed: {str(e)}",
                    step=step,
                    original_error=e
                )
        except TransactionError:
            raise
        
        except Exception as e:
            exc_type, exc_value, exc_traceback = sys.exc_info()
            tb_frames = traceback.extract_tb(exc_traceback)
            
            error_msg = (
                f"\nUnexpected error in execute_step:\n"
                f"Step details: {step}\n"
                f"Error type: {exc_type.__name__}\n"
                f"Error message: {str(e)}\n"
                f"Error location:\n{self.format_error_location(tb_frames)}"
            )
            
            logger.error(error_msg)
            raise TransactionError(
                message=f"Unexpected step execution error: {str(e)}",
                step=step,
                original_error=e
            )

    def build_filter_clauses(self, filter_values: List[Dict[str, Any]], table: Table) -> List[Any]:
        return self.build_filter_expressions(filter_values, table)

    def build_filter_expressions(self, filter_values: List[Dict[str, Any]], table: Table) -> List[Any]:
        filters = []
        for f in filter_values:
            if "type" in f:
                condition_type = f["type"]
                conditions = f.get("conditions", [])
                if condition_type == "and":
                    filters.extend(self.handle_conditions(conditions, table))
                elif condition_type == "or":
                    filters.append(or_(*self.handle_conditions(conditions, table)))
                else:
                    raise ValueError(f"不支持的条件类型: {condition_type}")
            else:
                column = table.c[f["field"]]
                value = convert_value(column.type, f["value"])
                if value:
                    filters.append(self.handle_operator(column, f["operator"], value))
        return filters

    def build_query(self, step: Dict[str, Any], table: Table) -> Any:
        """构建查询，包含详细的SQL输出"""
        try:
            logger.info(f"\n{'='*80}\nBuilding query for step: {step}\n{'='*80}")
            
            columns = []
            # logger.info("\nProcessing fields:")
            for f in step.get("fields", [{"field": "*"}]):
                try:
                    # logger.info(f"  Processing field: {f}")
                    
                    if 'table' in f:
                        t = Table(f["table"], self.metadata, autoload_with=self.engine)
                        # logger.info(f"    Using table: {f['table']}")
                    else:
                        t = table
                        # logger.info(f"    Using default table: {table.name}")
                        
                    if 'function' in f:
                        if f['function'].lower() == 'count':
                            if 'field' in f and f['field'] != '*':
                                column = func.count(t.c[f["field"]])
                                logger.info(f"    Creating COUNT of field: {f['field']}")
                            else:
                                column = func.count()
                                logger.info("    Creating COUNT(*)")
                        elif f['function'].lower() == 'sum':
                            column = func.sum(t.c[f["field"]])
                            logger.info(f"    Creating SUM of field: {f['field']}")
                        elif f['function'].lower() == 'avg':
                            column = func.avg(t.c[f["field"]])
                            logger.info(f"    Creating AVG of field: {f['field']}")
                        elif f['function'].lower() == 'min':
                            column = func.min(t.c[f["field"]])
                            logger.info(f"    Creating MIN of field: {f['field']}")
                        elif f['function'].lower() == 'max':
                            column = func.max(t.c[f["field"]])
                            logger.info(f"    Creating MAX of field: {f['field']}")
                        else:
                            raise ValueError(f"Unsupported function: {f['function']}")
                    else:
                        column = t.c[f["field"]]
                        logger.info(f"    Creating direct column reference: {f['field']}")
                        
                    if 'label' in f:
                        column = column.label(f['label'])
                        logger.info(f"    Adding label: {f['label']}")
                        
                    columns.append(column)
                    
                except KeyError as ke:
                    raise ValueError(f"Missing required field in query definition: {ke}")
                except Exception as e:
                    raise ValueError(f"Error processing field {f}: {str(e)}")

            query = select(*columns)
            logger.info("\nInitial SELECT query:")
            logger.info(str(query.compile(dialect=self.engine.dialect, compile_kwargs={"literal_binds": True})))

            # 处理 JOIN
            join = step.get("join")
            #print(join)
            if join:
                logger.info("\nProcessing JOINs:")
                for j in join:
                    #logger.info(f"  Processing join: {j}")
                    # print('Processing')
                    left_table = Table(j["left_table"], self.metadata, autoload_with=self.engine)
                    right_table = Table(j["right_table"], self.metadata, autoload_with=self.engine)
                    join_on = [left_table.c[o["left_column"]] == right_table.c[o["right_column"]] for o in j["on"]]
                    query = query.join(right_table, and_(*join_on), isouter=j["type"] == "left")
                    #logger.info("  Query after join:")
                    #logger.info(str(query.compile(dialect=self.engine.dialect, compile_kwargs={"literal_binds": True})))

            # 处理 WHERE 条件
            filter_values = step.get("filter_values", [])
            if filter_values:
                logger.info("\nProcessing WHERE conditions:")
                filters = self.build_filter_expressions(filter_values, table)
                if filters:
                    query = query.where(*filters)
                    logger.info("  Query after where:")
                    logger.info(str(query.compile(dialect=self.engine.dialect, compile_kwargs={"literal_binds": True})))

            # 处理 GROUP BY
            if any('function' in f for f in step.get("fields", [])):
                group_by_columns = []
                logger.info("\nProcessing GROUP BY:")
                for f in step.get("fields", []):
                    if 'function' not in f and 'field' in f:
                        if 'table' in f:
                            t = Table(f["table"], self.metadata, autoload_with=self.engine)
                        else:
                            t = table
                        group_by_columns.append(t.c[f["field"]])
                        logger.info(f"  Adding group by column: {f['field']}")
                
                if group_by_columns:
                    query = query.group_by(*group_by_columns)
                    logger.info("  Query after group by:")
                    logger.info(str(query.compile(dialect=self.engine.dialect, compile_kwargs={"literal_binds": True})))

            # 处理 ORDER BY
            order_by = step.get("order_by", [])
            if order_by:
                logger.info("\nProcessing ORDER BY:")
                order_columns = []
                for order in order_by:
                    if 'table' in order:
                        t = Table(order["table"], self.metadata, autoload_with=self.engine)
                    else:
                        t = table
                    column = t.c[order["field"]]
                    if order.get("direction", "asc").lower() == "desc":
                        column = column.desc()
                    order_columns.append(column)
                    logger.info(f"  Adding order by column: {order['field']} {order.get('direction', 'asc')}")
                
                query = query.order_by(*order_columns)
                logger.info("  Query after order by:")
                logger.info(str(query.compile(dialect=self.engine.dialect, compile_kwargs={"literal_binds": True})))

            # 处理 LIMIT 和 OFFSET
            if "limit" in step:
                query = query.limit(step["limit"])
                logger.info(f"\nAdding LIMIT {step['limit']}")

            if "offset" in step:
                query = query.offset(step["offset"])
                logger.info(f"Adding OFFSET {step['offset']}")

            # 输出最终的SQL查询
            logger.info("\nFinal SQL Query:")
            final_sql = str(query.compile(dialect=self.engine.dialect, compile_kwargs={"literal_binds": True}))
            logger.info(f"\n{'-'*40}\n{final_sql}\n{'-'*40}\n")
            
            return query
            
        except Exception as e:
            exc_type, exc_value, exc_traceback = sys.exc_info()
            tb_frames = traceback.extract_tb(exc_traceback)
            
            error_msg = (
                f"\nError building query:\n"
                f"Step details: {step}\n"
                f"Error type: {exc_type.__name__}\n"
                f"Error message: {str(e)}\n"
                f"Error location:\n{self.format_error_location(tb_frames)}"
            )
            
            logger.error(error_msg)
            raise TransactionError(
                message=f"Query building failed: {str(e)}",
                step=step,
                original_error=e
            )

    def handle_conditions(self, conditions: List[Dict[str, Any]], table: Table) -> List[Any]:
        return self.build_filter_expressions(conditions, table)

    def handle_operator1(self, column: Any, operator: str, value: Any) -> Any:
        operators = {
            "eq": column.__eq__,
            "ne": column.__ne__,
            "lt": column.__lt__,
            "gt": column.__gt__,
            "le": column.__le__,
            "ge": column.__ge__,
            "like": column.like,
            "ilike": column.ilike,
            "in": column.in_,
            "not_in": lambda x: ~column.in_(x),
            "is_null": lambda: column.is_(None),
            "is_not_null": lambda: column.isnot(None)
        }
        try:
            return operators[operator](value)
        except KeyError:
            raise ValueError(f"不支持的操作符: {operator}")
            
    def handle_operator(self, column: Any, operator: str, value: Any) -> Any:
        # 定义支持的操作符字典，键为操作符名称，值为相应的SQLAlchemy表达式
        operators = {
            "eq": column.__eq__,        # 等于（=），用于判断字段值是否等于指定值
            "ne": column.__ne__,        # 不等于（!=），用于判断字段值是否不等于指定值
            "lt": column.__lt__,        # 小于（<），用于判断字段值是否小于指定值
            "gt": column.__gt__,        # 大于（>），用于判断字段值是否大于指定值
            "le": column.__le__,        # 小于或等于（<=），用于判断字段值是否小于或等于指定值
            "ge": column.__ge__,        # 大于或等于（>=），用于判断字段值是否大于或等于指定值
            "like": column.like,        # 模糊匹配，用于检查字段值是否包含指定的部分值（区分大小写）
            "ilike": column.ilike,      # 不区分大小写的模糊匹配，用于检查字段值是否包含指定的部分值
            "in": column.in_,           # 包含于集合，用于判断字段值是否在指定集合中
            "not_in": lambda x: ~column.in_(x),  # 不包含于集合，用于判断字段值是否不在指定集合中
            "is_null": lambda: column.is_(None), # 为空值，用于判断字段值是否为 NULL
            "is_not_null": lambda: column.isnot(None) # 不为空值，用于判断字段值是否不为 NULL
        }
        try:
            # 根据传入的操作符名称调用相应的表达式
            return operators[operator](value)
        except KeyError:
            # 如果操作符不支持，抛出异常
            raise ValueError(f"不支持的操作符: {operator}")

    def load_data_from_yaml(self, filename: str) -> Dict[str, Any]:
        try:
            with open(filename, "r") as file:
                return yaml.safe_load(file)
        except (FileNotFoundError, yaml.YAMLError) as e:
            logger.error(f"Error loading YAML data from {filename}: {e}")
            return {}

    def replace_dynamic_values1(self, condition, params):
        """
        递归地遍历 filter_values，替换 {{ search_term }} 等占位符
        """
        '''
        print('replace_dynamic_values')
        '''
        # 如果是一个条件字典
        if isinstance(condition, dict):
            # 处理嵌套的 conditions 列表
            if "conditions" in condition:
                for cond in condition["conditions"]:
                    self.replace_dynamic_values(cond, params)
            
            # 替换 `value` 中的占位符
            if "value" in condition and isinstance(condition["value"], str):
                # 替换 {{ search_term }} 为实际参数值
                #condition["value"] = condition["value"].replace("{{ search_term }}", params.get("search_term", ""))
                if isinstance(condition['value'], str):
                #and condition['value'].startswith('{{') and condition['value'].endswith('}}'):
                    matches = re.findall(r'\{\{(.*?)\}\}', condition['value'])
                    # 去除多余的空格
                    matches = [match.strip() for match in matches]
                    if matches:
                        param_name = matches[0].strip()
                                    
                        # param_name = condition['value'].strip('{} ')
                        
                        if param_name in params:
                          condition['value'] = params.get(param_name, condition['value'])
                        '''
                        else:
                          condition['field'] = '1'
                          condition['value'] = '1'
                        '''

    def replace_dynamic_values(self, condition, params):
        """
        递归地遍历 filter_values，替换 {{ status }} 等占位符。
        如果参数未赋值，则忽略该条件。
        """
        '''
        print('replace_dynamic_values')
        '''
        # 如果是一个条件字典
        if isinstance(condition, dict):
            # 处理嵌套的 conditions 列表
            if "conditions" in condition:
                # 遍历并过滤空参数的条件
                condition["conditions"] = [
                    self.replace_dynamic_values(cond, params) for cond in condition["conditions"]
                    if self.replace_dynamic_values(cond, params) is not None
                ]
            
            # 替换 `value` 中的占位符，或忽略该条件
            if "value" in condition and isinstance(condition["value"], str):
                param_name = re.findall(r"\{\{\s*(\w+)\s*\}\}", condition["value"])
                if param_name:
                    # 获取参数值
                    param_value = params.get(param_name[0], None)
                    
                    # 如果参数存在，则替换占位符；否则返回 None 表示忽略该条件
                    if param_value:
                        condition["value"] = condition["value"].replace(f"{{{{ {param_name[0]} }}}}", str(param_value))
                    else:
                        return None  # 忽略该条件
        elif isinstance(condition, str):
            #print(condition)
            param_name = re.findall(r"\{\{\s*(\w+)\s*\}\}", condition)
            if param_name:
                # 获取参数值
                param_value = params.get(param_name[0], None)
                
                # 如果参数存在，则替换占位符；否则返回 None 表示忽略该条件
                if param_value:
                    condition = condition.replace(f"{{{{ {param_name[0]} }}}}", str(param_value))
                else:
                    return None  # 忽略该条件

            pass
        
        return condition  # 返回更新后的条件
        
    def execute_transactions(
        self, 
        transaction_name: str = None,
        params: dict = None,
        config_file: str = None
    ):
        """执行事务，包含增强的错误处理"""
        try:
            logger.info(f"Starting transaction: {transaction_name} "
                    f"from config file: {config_file}")
            
            data = self.load_data_from_yaml(config_file)
            # print(data)

            if not data:
                raise TransactionError(
                    message=f"Failed to load configuration from {config_file}",
                    step=None
                )
                
            transaction_data = next((t for t in data.get("transactions", []) if t['name'] == transaction_name), None)

            if not transaction_data:
                raise TransactionError(
                    message=f"Transaction {transaction_name} not found in {config_file}",
                    step=None
                )
                
            #print(transaction_data)

            transaction = Transaction(**transaction_data)
            result = None
            
            #print(transaction)
            
            try:
                for step in transaction.steps:
                    #print(step)
                    if params:
                        # 替换参数和处理上传文件
                        if 'values' in step:
                            for key, value in step['values'].items():
                                
                                params_value = params.get(key, None)
                                
                                #if isinstance(params_value, UploadFile):
                                if type(params_value).__name__ == "UploadFile":
                                #if hasattr(params_value, "filename") and hasattr(params_value, "file"):
                                    
                                    step1 = {}
                                    step1['action'] = 'upload_file'
                                    step1['file'] = params_value #.get('file')
                                    step1['file_name'] = params_value.filename #get('file_name')
                                    step1['folder_path'] = "uploads/images"
                                    step['values'][key] = self.execute_step(step1)
                                    
                                else:
                                    step['values'][key] = None
                                    if 'data_from' in value:
                                        s_data_from = value['data_from']
                                        if 'data_key' in value:
                                            s_data_key = value['data_key']
                                            if s_data_from in gv.data:
                                                if s_data_key in gv.data[s_data_from]:
                                                    step['values'][key] = gv.data[s_data_from][s_data_key]
                                    else:      
                                        matches = re.findall(r'\{\{(.*?)\}\}', value)
                                        # 去除多余的空格
                                        matches = [match.strip() for match in matches]
                                        if matches:
                                            param_name = matches[0].strip()
                                            if isinstance(value, str) and param_name:
                                                if param_name in self.dynamic_values:
                                                    step['values'][key] = params.get(param_name, value)
                                                else:
                                                    step['values'][key] = params.get(param_name, '')
                                        else:
                                            param_name = value
                                            step['values'][key] = params.get(param_name, '')
                                        
                                            pass
                                    #print(step['values'][key])
                        '''     
                        if 'filter_values' in step:
                            print(step['filter_values'])
                            for filter_item in step['filter_values']:
                                print(filter_item)
                                if isinstance(filter_item['value'], str) and filter_item['value'].startswith('{{') and filter_item['value'].endswith('}}'):
                                    param_name = filter_item['value'].strip('{} ')
                                    print(param_name)
                                    filter_item['value'] = params.get(param_name, filter_item['value'])
                        '''
                        '''
                        # 替换 filter_values 中的占位符
                        if 'filter_values' in step:
                            for filter_item in step['filter_values']:
                                self.replace_dynamic_values(filter_item, params)
                        '''

                        # 在替换 filter_values 中的占位符时使用
                        if 'filter_values' in step:
                            step['filter_values'] = [
                                self.replace_dynamic_values(filter_item, params) for filter_item in step['filter_values']
                                if self.replace_dynamic_values(filter_item, params) is not None
                            ]

                        if 'limit' in step and 'limit' in params:
                            step['limit'] = params['limit']

                        if 'offset' in step and 'offset' in params:
                            step['offset'] = params['offset']

                        # if step['action'] == 'upload_file':
                        #     step['file'] = params.get('file')
                        #     step['file_name'] = params.get('file_name')
                        #     step['folder_path'] = params.get('folder_path')
                        
                        if step['action'] == 'execute':
                            step['sql'] = self.replace_dynamic_values(step['sql'], params)
                            #print(step['sql'])
                            
                    result = self.execute_step(step)
                    
                    if step["action"] == 'get':
                        result = [dict(row) for row in result]
                        
                        #print('==========data_to==========')
                        if step.get('data_to'):
                            gv.data[step.get('data_to')] = result
                            #print(gv.data[step.get('data_to')])
                        #print('==========data_to==========')
 
                    # logger.info(f"Step execution result: {result}")
            
                if self.db:
                    self.db.commit()

                # return result  # 返回最后一个步骤的结果
            except TransactionError as te:
                if self.db:
                    self.db.rollback()
                # 重新抛出，保留原始错误信息
                raise
        except TransactionError as te:
            print('TransactionError')
            # 记录详细错误信息并重新抛出
            error_msg = (
                f"\nTransaction execution failed: {transaction_name}\n"
                f"Config file: {config_file}\n"
                f"Original error: {str(te.original_error) if te.original_error else str(te)}\n"
                f"Step details: {te.step}\n"
                f"Error location:\n{self.format_error_location(te.traceback)}"
            )
            print(error_msg)
            logger.error(error_msg)
            raise
            
        except Exception as e:
            print('Exception')
            print(str(e))
            # 处理意外错误
            exc_type, exc_value, exc_traceback = sys.exc_info()
            tb_frames = traceback.extract_tb(exc_traceback)
            
            error_msg = (
                f"\nUnexpected error in transaction execution:\n"
                f"Transaction: {transaction_name}\n"
                f"Config file: {config_file}\n"
                f"Error type: {exc_type.__name__}\n"
                f"Error message: {str(e)}\n"
                f"Error location:\n{self.format_error_location(tb_frames)}"
            )
            
            logger.error(error_msg)
            if self.db:
                self.db.rollback()
            raise TransactionError(
                message=f"Unexpected transaction error: {str(e)}",
                step=None,
                original_error=e
            )
        except SQLAlchemyError as e:
            print('HTTPException')
            print(str(e))
            if self.db:
                self.db.rollback()
            logger.error(f"Error executing transaction {transaction_name} from {config_file}: {e}")
            raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
        except HTTPException as e:
            print('HTTPException')
            print(str(e))
            # 重新抛出 HTTP 异常
            raise he
        except Exception as e:
            print('Exception')
            print(str(e))
            
            if self.db:
                self.db.rollback()
            logger.error(f"Unexpected error executing transaction {transaction_name} from {config_file}: {e}")
            raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")
        finally:
            # print('all finish')
            return result
    
# if __name__ == "__main__":
#     uvicorn.run(app, host="0.0.0.0", port=8000)
