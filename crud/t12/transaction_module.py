import uvicorn
from fastapi import FastAPI, Depends, HTTPException, Response, Form
from fastapi import UploadFile, File
from fastapi.responses import FileResponse
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import shutil
import os
from sqlalchemy import create_engine, MetaData, Table, select, and_, or_
from sqlalchemy.sql import text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import SQLAlchemyError
import yaml
import logging
from typing import List, Dict, Any, Union
import traceback

import gv as gv

gv.data = {}

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Define database URL constant
SQLALCHEMY_DATABASE_URL = "sqlite:///./Chinook.db"

# Create FastAPI application instance
app = FastAPI()


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory="static"), name="static")
# app.mount("/", StaticFiles(directory="static",html = True), name="static")

# Create database connection engine
engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create Metadata instance
metadata = MetaData()

# Create database tables
metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def load_data_from_yaml1(filename: str = "chinook.yaml") -> Dict[str, Any]:
    try:
        with open(filename, "r") as file:
            return yaml.safe_load(file)
    except (FileNotFoundError, yaml.YAMLError) as e:
        logger.error(f"Error loading YAML data: {e}")
        return {}

class Transaction:
    def __init__(self, name: str, steps: List[Dict[str, Any]]):
        self.name = name
        self.steps = steps

from fastapi import UploadFile, File, HTTPException
from fastapi.responses import FileResponse
import shutil
import os
from typing import List
import magic


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
    
    

def execute_step(step: Dict[str, Any], db: SessionLocal = None) -> Any:
    action = step["action"]
    if step.get('table'):
        table = Table(step["table"], metadata, autoload_with=engine)
    
    try:
        if action == "insert":
            result = db.execute(table.insert().values(**step["values"]))
            return result.rowcount
        elif action == "update":
            filters = build_filter_clauses(step.get("filter_values", []), table)
            result = db.execute(table.update().where(*filters).values(**step["values"]))
            return result.rowcount
        elif action == "delete":
            filters = build_filter_clauses(step.get("filter_values", []), table)
            result = db.execute(table.delete().where(*filters))
            return result.rowcount
        elif action == "get":
            query = build_query(step, table)
            result = db.execute(query).mappings().all()
            if step.get('data_to'):
                gv.data[step.get('data_to')] = result
            return result
        elif action == "get2":
            query = select([table])
            if "filter_values" in step:
                filters = build_filter_clauses(step["filter_values"], table)
                query = query.where(*filters)
            if "fields" in step:
                columns = [table.c[field] for field in step["fields"]]
                query = query.with_only_columns(*columns)
            result = db.execute(query).fetchall()
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
                filters = build_filter_clauses(step["filter_values"], table)
                query = query.where(*filters)

            result = db.execute(query).fetchall()
            if step.get('data_to'):
                gv.data[step.get('data_to')] = result
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
            if sql:
                result = db.execute(text(sql))
                return result.rowcount
            else:
                raise ValueError("SQL statement is missing for execute action")
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
            file: UploadFile = step.get("file")
            destination: str = step.get("folder_path", "") + '/' + step.get("file_name", "")
            if not file:
                raise ValueError("No file provided for upload")
            if not destination:
                raise ValueError("No destination provided for file upload")
            
            # 文件类型验证
            if not allowed_file(file.filename):
                raise ValueError(f"File type not allowed. Allowed types are: {', '.join(ALLOWED_EXTENSIONS)}")
            
            # # 文件内容类型验证
            # if not validate_file_type(file):
            #     raise ValueError("File content does not match the allowed types")
            
            # 文件大小验证
            if not validate_file_size(file):
                raise ValueError(f"File size exceeds the maximum limit of {MAX_FILE_SIZE / (1024 * 1024)} MB")
            
            os.makedirs(os.path.dirname(destination), exist_ok=True)
            with open(destination, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)

            return {"filename": file.filename, "destination": destination}

        elif action == "download_file":
            file_path: str = step.get("file_path", "")
            if not file_path or not os.path.exists(file_path):
                raise ValueError(f"File not found: {file_path}")
            
            # 验证文件类型（可选，取决于您的需求）
            if not allowed_file(file_path):
                raise ValueError(f"File type not allowed for download. Allowed types are: {', '.join(ALLOWED_EXTENSIONS)}")
            
            return FileResponse(file_path, filename=os.path.basename(file_path))
        else:
            raise ValueError(f"不支持的操作: {action}")
    except Exception as e:
        logger.error(f"执行步骤时出错: {e}")
        raise e

def build_filter_clauses(filter_values: List[Dict[str, Any]], table: Table) -> List[Any]:
    return build_filter_expressions(filter_values, table)

def build_filter_expressions(filter_values: List[Dict[str, Any]], table: Table) -> List[Any]:
    filters = []
    for f in filter_values:
        if "type" in f:
            condition_type = f["type"]
            conditions = f.get("conditions", [])
            if condition_type == "and":
                filters.extend(handle_conditions(conditions, table))
            elif condition_type == "or":
                filters.append(or_(*handle_conditions(conditions, table)))
            else:
                raise ValueError(f"不支持的条件类型: {condition_type}")
        else:
            column = table.c[f["field"]]
            value = convert_value(column.type, f["value"])
            filters.append(handle_operator(column, f["operator"], value))
    return filters

def build_query(step: Dict[str, Any], table: Table) -> Any:
    print('build_query')
    columns = []
    for f in step.get("fields", [{"field": "*"}]):
        print(f)
        if 'table' in f:
            t = Table(f["table"], metadata, autoload_with=engine)
        else:
            t = table
        if 'label' in f:
            columns.append(t.c[f["field"]].label(f['label']))
        else:
            columns.append(t.c[f["field"]])

    #query = select(*[table.c[f["field"]] for f in step.get("fields", [{"field": "*"}])])
    query = select(*columns)

    join = step.get("join")
    print(join)
    if join:
        for j in join:
            left_table = Table(j["left_table"], metadata, autoload_with=engine)
            right_table = Table(j["right_table"], metadata, autoload_with=engine)
            join_on = [left_table.c[o["left_column"]] == right_table.c[o["right_column"]] for o in j["on"]]
            query = query.join(right_table, and_(*join_on), isouter=j["type"] == "left")

    filter_values = step.get("filter_values", [])
    print('filter_values')
    print(filter_values)
    filters = build_filter_expressions(filter_values, table)

    print(filters)
    if filters:
        query = query.filter(*filters)

    return query

def handle_conditions(conditions: List[Dict[str, Any]], table: Table) -> List[Any]:
    return build_filter_expressions(conditions, table)

def convert_value1(column_type: Any, value: Any) -> Any:
    python_type = column_type.python_type
    try:
        return python_type(value)
    except ValueError:
        return value
        
from sqlalchemy import BLOB, Date, Time, DateTime, Interval
from datetime import datetime, date, time, timedelta
import re
from typing import Any

def convert_value(column_type: Any, value: Any) -> Any:
    if value == 'None' or value is None:
        return None
    print(column_type)
    print(value)
    if isinstance(column_type, BLOB):
        if isinstance(value, str):
            return value.encode('utf-8')
        elif isinstance(value, bytes):
            return value
        else:
            raise ValueError(f"无法将 {type(value)} 转换为 BLOB 类型")

    elif isinstance(column_type, Date):
        
        if isinstance(value, str):
            print(value)
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

            
def handle_operator(column: Any, operator: str, value: Any) -> Any:
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

import traceback
import yaml
from typing import Dict, Any

def load_data_from_yaml(filename: str) -> Dict[str, Any]:
    try:
        with open(filename, "r") as file:
            return yaml.safe_load(file)
    except (FileNotFoundError, yaml.YAMLError) as e:
        logger.error(f"Error loading YAML data from {filename}: {e}")
        return {}



@app.get("/a")
def execute_transactions1(db: SessionLocal = Depends(get_db), transaction_name: str = None, params: dict = None, config_file: str = "chinook.yaml"):
    try:
        data = load_data_from_yaml(config_file)
        transaction_data = next((t for t in data.get("transactions", []) if t['name'] == transaction_name), None)
        if not transaction_data:
            raise ValueError(f"Transaction {transaction_name} not found in {config_file}")

        transaction = Transaction(**transaction_data)
        for step in transaction.steps:
            # 替换 values 中的参数
            if 'values' in step:
                for key, value in step['values'].items():
                    if isinstance(value, str) and value.startswith('{{') and value.endswith('}}'):
                        param_name = value.strip('{} ')
                        step['values'][key] = params.get(param_name, value)
            
            # 替换 filter_values 中的参数
            if 'filter_values' in step:
                for filter_item in step['filter_values']:
                    if isinstance(filter_item['value'], str) and filter_item['value'].startswith('{{') and filter_item['value'].endswith('}}'):
                        param_name = filter_item['value'].strip('{} ')
                        filter_item['value'] = params.get(param_name, filter_item['value'])
            
            result = execute_step(step, db)
            logger.info(f"Step execution result: {result}")
        
        db.commit()
        return result  # 返回最后一个步骤的结果
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"Error executing transaction {transaction_name} from {config_file}: {e}")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    except Exception as e:
        db.rollback()
        logger.error(f"Unexpected error executing transaction {transaction_name} from {config_file}: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.post("/b")
async def execute_transactions2(
    db: SessionLocal = Depends(get_db),
    transaction_name: str = None,
    params: dict = None,
    config_file: str = "chinook.yaml",
    uploaded_file: UploadFile = File(None)
):
    try:
        data = load_data_from_yaml(config_file)
        transaction_data = next((t for t in data.get("transactions", []) if t['name'] == transaction_name), None)
        if not transaction_data:
            raise ValueError(f"Transaction {transaction_name} not found in {config_file}")

        transaction = Transaction(**transaction_data)
        for step in transaction.steps:
            # 替换参数和处理上传文件
            if 'values' in step:
                for key, value in step['values'].items():
                    if isinstance(value, str) and value.startswith('{{') and value.endswith('}}'):
                        param_name = value.strip('{} ')
                        step['values'][key] = params.get(param_name, value)
            
            if 'filter_values' in step:
                for filter_item in step['filter_values']:
                    if isinstance(filter_item['value'], str) and filter_item['value'].startswith('{{') and filter_item['value'].endswith('}}'):
                        param_name = filter_item['value'].strip('{} ')
                        filter_item['value'] = params.get(param_name, filter_item['value'])
            
            if step['action'] == 'upload_file':
                step['file'] = uploaded_file
            
            result = execute_step(step, db)
            logger.info(f"Step execution result: {result}")
        
        db.commit()
        return result  # 返回最后一个步骤的结果
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"Error executing transaction {transaction_name} from {config_file}: {e}")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    except Exception as e:
        db.rollback()
        logger.error(f"Unexpected error executing transaction {transaction_name} from {config_file}: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

# @app.post("/")
def execute_transactions(
    db: SessionLocal = None,
    transaction_name: str = None,
    params: dict = None,
    config_file: str = None
):
    try:
        #if db is None:
        #  db = Depends(get_db)
          
        data = load_data_from_yaml(config_file)
        transaction_data = next((t for t in data.get("transactions", []) if t['name'] == transaction_name), None)
        if not transaction_data:
            raise ValueError(f"Transaction {transaction_name} not found in {config_file}")

        transaction = Transaction(**transaction_data)
        for step in transaction.steps:
            # 替换参数和处理上传文件
            if 'values' in step:
                for key, value in step['values'].items():
                    if isinstance(value, str) and value.startswith('{{') and value.endswith('}}'):
                        param_name = value.strip('{} ')
                        step['values'][key] = params.get(param_name, value)
            
            if 'filter_values' in step:
                for filter_item in step['filter_values']:
                    if isinstance(filter_item['value'], str) and filter_item['value'].startswith('{{') and filter_item['value'].endswith('}}'):
                        param_name = filter_item['value'].strip('{} ')
                        filter_item['value'] = params.get(param_name, filter_item['value'])
            
            if step['action'] == 'upload_file':
                step['file'] = params.get('file')
                step['file_name'] = params.get('file_name')
                step['folder_path'] = params.get('folder_path')
            
            try:
                result = execute_step(step, db)
                logger.info(f"Step execution result: {result}")
                return result
            except ValueError as ve:
                # 捕获文件验证相关的错误
                logger.error(f"File validation error: {str(ve)}")
                raise HTTPException(status_code=400, detail=str(ve))
        
        if db:
          db.commit()
        return result  # 返回最后一个步骤的结果
    except SQLAlchemyError as e:
        if db:
          db.rollback()
        logger.error(f"Error executing transaction {transaction_name} from {config_file}: {e}")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    except HTTPException as he:
        # 重新抛出 HTTP 异常
        raise he
    except Exception as e:
        
        if db:
          db.rollback()
        logger.error(f"Unexpected error executing transaction {transaction_name} from {config_file}: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
