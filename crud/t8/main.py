# main.py
from fastapi import FastAPI, Request, Form, HTTPException
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from sqlalchemy import create_engine, MetaData, Table, select, insert, update, delete, inspect, or_, func
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import SQLAlchemyError
from typing import List, Dict, Any
import json
import os

# Import the new table configuration generator
from table_config_generator import generate_all_table_configs

app = FastAPI()
templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")

# 添加 min 函数到模板上下文
templates.env.globals['min'] = min

# Database connection configuration
DATABASE_URL = "sqlite:///./Chinook.db"
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
metadata = MetaData()

# Reflect existing database tables
metadata.reflect(bind=engine)

# Generate table configurations
generate_all_table_configs(engine)

def get_table_config(table_name):
    with open(f'table_configs/{table_name}_config.json', 'r') as f:
        return json.load(f)

def get_primary_key(table):
    return next(iter(table.primary_key.columns)).name

def get_table_names():
    inspector = inspect(engine)
    return inspector.get_table_names()

@app.get("/")
async def read_root(request: Request):
    tables = get_table_names()
    return templates.TemplateResponse("all_in_one.html", {"request": request, "tables": tables})

@app.get("/table/{table_name}")
async def read_table(request: Request, table_name: str):
    if table_name not in metadata.tables:
        raise HTTPException(status_code=404, detail="Table not found")
    
    table_config = get_table_config(table_name)
    return templates.TemplateResponse("all_in_one.html", {
        "request": request,
        "table_name": table_name,
        "table_config": table_config
    })

@app.get("/table_content/{table_name}")
async def read_table_content(request: Request, table_name: str, page: int = 1, search: str = '', page_size: int = 10):
    if table_name not in metadata.tables:
        raise HTTPException(status_code=404, detail="Table not found")
    
    table_config = get_table_config(table_name)
    
    table = metadata.tables[table_name]
    table_config = get_table_config(table_name)
    primary_key = next(col['name'] for col in table_config['columns'] if col['primary_key'])
    offset = (page - 1) * page_size
    
    query = select(table.columns)
    
    if search:
        search_columns = [getattr(table.c, col).ilike(f"%{search}%") for col in table.columns.keys()]
        query = query.where(or_(*search_columns))
    
    with SessionLocal() as session:
        count_query = select(func.count()).select_from(query.alias())
        total_items = session.execute(count_query).scalar()
        result = session.execute(query.offset(offset).limit(page_size)).fetchall()
        
    total_pages = (total_items + page_size - 1) // page_size
    print(result)
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
        "search": search,
        "table_config": table_config
    })


'''
# main.py
from fastapi import FastAPI, Request, Form, HTTPException
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from sqlalchemy import create_engine, MetaData, Table, select, insert, update, delete, inspect, or_, func
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import SQLAlchemyError
from typing import List, Dict, Any

app = FastAPI()
templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")

# Database connection configuration
DATABASE_URL = "sqlite:///./Chinook.db"
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
metadata = MetaData()

# Reflect existing database tables
metadata.reflect(bind=engine)

def get_primary_key(table):
    return next(iter(table.primary_key.columns)).name

def get_table_names():
    inspector = inspect(engine)
    return inspector.get_table_names()

@app.get("/")
async def read_root(request: Request):
    tables = get_table_names()
    return templates.TemplateResponse("all_in_one.html", {"request": request, "tables": tables})

# 添加 min 函数到模板上下文
templates.env.globals['min'] = min

@app.get("/table/{table_name}")
async def read_table(request: Request, table_name: str):
    if table_name not in metadata.tables:
        raise HTTPException(status_code=404, detail="Table not found")
    
    return templates.TemplateResponse("all_in_one.html", {
        "request": request,
        "table_name": table_name,
    })

@app.get("/table_content/{table_name}")
async def read_table_content(request: Request, table_name: str, page: int = 1, search: str = '', page_size: int = 10):
    if table_name not in metadata.tables:
        raise HTTPException(status_code=404, detail="Table not found")
    
    table = metadata.tables[table_name]
    primary_key = get_primary_key(table)
    offset = (page - 1) * page_size
    
    query = select(table.columns)
    
    if search:
        search_columns = [getattr(table.c, col).ilike(f"%{search}%") for col in table.columns.keys()]
        query = query.where(or_(*search_columns))
    
    with SessionLocal() as session:
        count_query = select(func.count()).select_from(query.alias())
        total_items = session.execute(count_query).scalar()
        result = session.execute(query.offset(offset).limit(page_size)).fetchall()
        columns = table.columns.keys()
        
    total_pages = (total_items + page_size - 1) // page_size
    
    return templates.TemplateResponse("table_content.html", {
        "request": request,
        "table_name": table_name,
        "columns": columns,
        "rows": result,
        "primary_key": primary_key,
        "page": page,
        "page_size": page_size,
        "total_items": total_items,
        "total_pages": total_pages,
        "search": search,
    })
'''

@app.get("/create/{table_name}")
async def create_form(request: Request, table_name: str):
    if table_name not in metadata.tables:
        raise HTTPException(status_code=404, detail="Table not found")
    
    table = metadata.tables[table_name]
    columns = [col.name for col in table.columns if col.name != get_primary_key(table)]
    return templates.TemplateResponse("create_form.html", {
        "request": request, 
        "table_name": table_name, 
        "columns": columns,
    })

@app.post("/create/{table_name}")
async def create_item(table_name: str, request: Request):
    if table_name not in metadata.tables:
        raise HTTPException(status_code=404, detail="Table not found")
    
    table = metadata.tables[table_name]
    form_data = await request.form()
    data = {key: value for key, value in form_data.items() if key in table.columns.keys()}
    
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
        return {"success": False, "message": str(e)}

@app.get("/edit/{table_name}/{id}")
async def edit_form(request: Request, table_name: str, id: str, page: int = 1, search: str = '', page_size: int = 10):
    if table_name not in metadata.tables:
        raise HTTPException(status_code=404, detail="Table not found")
    
    table_config = get_table_config(table_name)
    
    table = metadata.tables[table_name]
    primary_key = get_primary_key(table)
    
    with SessionLocal() as session:
        stmt = select(table).where(getattr(table.c, primary_key) == id)
        result = session.execute(stmt).fetchone()._asdict()
    
    data = dict(result)
    
    '''
    for key in data:
        if data[key] is None:
            data[key] = ''
    '''
    
    if result:
        return templates.TemplateResponse("edit_form.html", {
            "request": request,
            "table_name": table_name,
            "id": id,
            "item": data,
            "primary_key": primary_key,
            "page": page,
            "page_size": page_size,
            "search": search,
            "table_config": table_config
        })
    raise HTTPException(status_code=404, detail="Item not found")

@app.post("/edit/{table_name}/{id}")
async def edit_item(table_name: str, id: str, request: Request):
    print('edit_item')
    if table_name not in metadata.tables:
        raise HTTPException(status_code=404, detail="Table not found")
    
    table = metadata.tables[table_name]
    print(table)
    primary_key = get_primary_key(table)
    print(primary_key)
    form_data = await request.form()
    data = {key: value for key, value in form_data.items() if key in table.columns.keys()}
    print(data)
    
    for key in data:
        print(key)
        data[key] = convert_value(table.c[key].type, data[key])
        print(data[key])
        #if data[key] is '':
        #    data[key] = None
    
    try:
        with SessionLocal() as session:
            stmt = update(table).where(getattr(table.c, primary_key) == id).values(**data)
            print(stmt)
            print(session.execute(stmt))
            session.commit()
            return ''
            '''
            return templates.TemplateResponse("table_content.html", {
                "request": request,
                "table_name": table_name,
                "columns": table.columns.keys(),
                "rows": session.execute(select(table)).fetchall(),
                "primary_key": primary_key,
                "page": 1,
                "page_size": 10,
                "total_items": session.execute(select(func.count()).select_from(table)).scalar(),
                "total_pages": 1,
                "search": "",
            })
            '''
    except SQLAlchemyError as e:
        print(e)
        return {"success": False, "message": str(e)}

# ... (rest of the file remains the same)

@app.delete("/delete/{table_name}/{id}")
async def delete_item(table_name: str, id: str):
    if table_name not in metadata.tables:
        raise HTTPException(status_code=404, detail="Table not found")
    
    table = metadata.tables[table_name]
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


# main.py (在已有代码的基础上添加)

from sqlalchemy import inspect
from sqlalchemy.orm import class_mapper
from sqlalchemy.sql.sqltypes import String, Integer, Boolean, DateTime, Date

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

import uvicorn

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
