# main.py
from fastapi import FastAPI, HTTPException, Request, Depends
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from sqlalchemy import create_engine, MetaData, Table, select, insert, update, delete, or_, and_, inspect, func, asc, desc, DateTime
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.types import String, Text
import sqlalchemy
from typing import List, Dict
import logging
import types
from datetime import datetime
import pycountry
import csv
import io

app = FastAPI()

app.mount(path="/static", app=StaticFiles(directory="static"), name="static")

templates = Jinja2Templates(directory="templates")

# 配置日志记录
logging.basicConfig(level=logging.INFO)
logging.getLogger("sqlalchemy.engine").setLevel(logging.DEBUG)

DATABASE_URL = "sqlite:///./my_database.db"
engine = create_engine(DATABASE_URL, echo=True)
metadata = MetaData()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

metadata.reflect(bind=engine)
table_names = metadata.tables.keys()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request, "table_names": table_names})

@app.get("/a", response_class=HTMLResponse)
def index(request: Request):
    with open("static/a.html", "r", encoding="utf-8") as f:
        html = f.read()
    return HTMLResponse(html)

import json
import os
from sqlalchemy import inspect

# 缓存国家列表数据
countries_cache = None

def get_column_info(table):
    global countries_cache

    # 检查 JSON 文件是否存在
    if os.path.exists(f'{table.name}.json'):
        # 如果存在,则从 JSON 文件中读取列信息
        with open(f'{table.name}.json') as f:
            column_info = json.load(f)

            for c in column_info:
                if 'data_source' in c:
                    if c['data_source'] == 'countries':
                        # 如果国家列表数据尚未缓存,则从文件中读取并缓存
                        if countries_cache is None:
                            if os.path.exists('countries.json'):
                                with open('countries.json') as file:
                                    countries_cache = json.load(file)
                            else:
                                # 获取 ISO 国家列表
                                countries = list(pycountry.countries)

                                # 提取国家名称
                                country_names = [country.name for country in countries]

                                # 写入到 JSON 文件
                                with open('countries.json', 'w') as file:
                                    json.dump(country_names, file, indent=4)

                                countries_cache = country_names

                        c['form_element']['options'] = countries_cache

            return column_info
    else:
        # 如果不存在,则从数据库中获取列信息
        columns = table.columns
        column_info = []
        for c in columns:
            column_info.append({
                'name': c.name,
                'label': c.name.replace('_', ' ').title(),  # 使用更友好的列标签
                'type': str(c.type),
                'required': c.nullable == False,
                'primary_key': c.primary_key,
                'max_length': getattr(c.type, 'length', None)  # 获取字符串长度限制
            })
        # 将列信息保存到 JSON 文件中
        with open(f'{table.name}.json', 'w') as f:
            json.dump(column_info, f, ensure_ascii=False, indent=4, sort_keys=True, separators=(',', ': '))
        return column_info

@app.get("/table/{table_name}", response_class=HTMLResponse)
def table_view(request: Request,
               table_name: str,
               page: int = 1,
               per_page: int = 10,
               sort_column: str = None,
               sort_order: str = None,
               query: str = None,
               db: Session = Depends(get_db)):
    table = Table(table_name, metadata, autoload_with=engine)
    stmt = select(table)

    column_info = get_column_info(table)

    total_results = None  # 初始值设为 None

    # 构建搜索条件
    if query is not None:
        conditions = []
        for column in table.columns:
            if isinstance(column.type, (sqlalchemy.sql.sqltypes.String, sqlalchemy.sql.sqltypes.TEXT, sqlalchemy.sql.sqltypes.NVARCHAR)):
                column_conditions = or_(column.contains(query), column.ilike(f"%{query}%"))
                conditions.append(column_conditions)
        if conditions:
            stmt = stmt.where(or_(*conditions))
            # 在应用搜索条件后计算总结果数
            total_results = db.query(func.count()).select_from(table).filter(*conditions).scalar()

    if total_results is None:  # 如果没有应用搜索条件,则计算全部结果数
        total_results = db.query(func.count()).select_from(table).scalar()

    # 构建排序条件
    if sort_column:
        sort_column_obj = getattr(table.c, sort_column)
        if sort_order == "asc":# main.py(继续)
            stmt = stmt.order_by(asc(sort_column_obj))
        elif sort_order == "desc":
            stmt = stmt.order_by(desc(sort_column_obj))

    # 构建分页条件
    stmt = stmt.limit(per_page).offset((page - 1) * per_page)

    # 自动检测日期时间列并进行格式化
    for column in table.columns:
        if isinstance(column.type, (sqlalchemy.sql.sqltypes.DateTime)):
            stmt = stmt.column(func.strftime('%Y-%m-%dT%H:%M', column))

    # 执行查询并获取结果
    results = db.execute(stmt).mappings().all()

    # 获取主键列名
    primary_key = next((column.name for column in table.columns if column.primary_key), None)

    # 计算分页相关数据
    total_pages = total_results // per_page + (total_results % per_page > 0)
    start_page = max(1, page - 2)
    end_page = min(total_pages, page + 2)
    if end_page - start_page < 4:
        if start_page > 1:
            start_page = max(1, end_page - 4)
        end_page = min(total_pages, start_page + 4)

    # 渲染模板
    return templates.TemplateResponse("table_view.html", {
        "request": request,
        "table_name": table_name,
        "columns": table.columns,
        "column_info": column_info,
        "results": results,
        "primary_key": primary_key,
        "total_results": total_results,
        "page": page,
        "per_page": per_page,
        "sort_column": sort_column,
        "sort_order": sort_order,
        "start_page": start_page,
        "end_page": end_page,
        "total_pages": total_pages
    })

# @app.post("/table/{table_name}/insert", response_class=HTMLResponse)
# async def insert_record(request: Request, table_name: str, db: Session = Depends(get_db)):
#     form_data = await request.form()
#     data_dict = {}

#     # for key, value in form_data.items():
#     #     data_dict[key] = value

#     # 验证和过滤用户输入
#     for key, value in form_data.items():
#         data_dict[key] = sanitize_input(value)  # 调用输入验证和过滤函数

#     print(data_dict)

#     table = Table(table_name, metadata, autoload_with=engine)
#     try:
#         stmt = insert(table).values(data_dict)
#         db.execute(stmt)
#         db.commit()
#     except SQLAlchemyError as e:
#         raise HTTPException(status_code=500, detail=str(e))

#     return templates.TemplateResponse("insert_success.html", {"request": request, "table_name": table_name})

@app.post("/table/{table_name}/insert", response_class=HTMLResponse)
async def insert_record(request: Request, table_name: str, db: Session = Depends(get_db)):
    form_data = await request.form()
    data_dict = {}

    # 验证和过滤用户输入
    for key, value in form_data.items():
        data_dict[key] = sanitize_input(value)

    table = Table(table_name, metadata, autoload_with=engine)
    primary_key = get_primary_key(table)

    # 如果主键值为空,则从data_dict中删除该键值对,让数据库自动生成主键
    if primary_key in data_dict and data_dict[primary_key] == '':
        del data_dict[primary_key]

    try:
        stmt = insert(table).values(data_dict)
        db.execute(stmt)
        db.commit()
    except SQLAlchemyError as e:
        raise HTTPException(status_code=500, detail=str(e))

    return templates.TemplateResponse("insert_success.html", {"request": request, "table_name": table_name})
    
def get_primary_key(table):
    for column in table.columns:
        if column.primary_key:
            return column.name
    return None

@app.post("/table/{table_name}/update", response_class=HTMLResponse)
async def update_record(request: Request, table_name: str, db: Session = Depends(get_db)):
    form_data = await request.form()
    data_dict = {}

    # 读取 JSON 文件
    with open(f'{table_name}.json', 'r') as file:
        data_json = json.load(file)

    # 创建一个空字典
    column_dict = {item['name']: item for item in data_json}

    table = Table(table_name, metadata, autoload_with=engine)
    primary_key = get_primary_key(table)
    primary_key_value = form_data.get(primary_key)

    for key, value in form_data.items():
        if key != primary_key:
            if column_dict[key]['type'] == 'DATETIME':
                data_dict[key] = datetime.strptime(sanitize_input(value), '%Y-%m-%dT%H:%M')
            else:
                data_dict[key] = sanitize_input(value)  # 调用输入验证和过滤函数

    try:
        stmt = update(table).where(getattr(table.c, primary_key) == primary_key_value).values(data_dict)
        db.execute(stmt)
        db.commit()
    except SQLAlchemyError as e:
        raise HTTPException(status_code=500, detail=str(e))

    return templates.TemplateResponse("update_success.html", {"request": request, "table_name": table_name})

@app.post("/table/{table_name}/delete", response_class=HTMLResponse)
async def delete_record(request: Request, table_name: str, db: Session = Depends(get_db)):
    form_data = await request.form()
    table = Table(table_name, metadata, autoload_with=engine)
    primary_key = get_primary_key(table)
    primary_key_value = form_data.get(primary_key)

    try:
        stmt = delete(table).where(getattr(table.c, primary_key) == sanitize_input(primary_key_value))
        db.execute(stmt)
        db.commit()
    except SQLAlchemyError as e:
        raise HTTPException(status_code=500, detail=str(e))

    return templates.TemplateResponse("delete_success.html", {"request": request, "table_name": table_name})

@app.get("/table/{table_name}/search", response_class=HTMLResponse)
def search_records(request: Request, table_name: str, query: str, db: Session = Depends(get_db)):
    table = Table(table_name, metadata, autoload_with=engine)
    stmt = select(table)
    conditions = []
    for column in table.columns:
        if isinstance(column.type, (sqlalchemy.sql.sqltypes.String, sqlalchemy.sql.sqltypes.TEXT, sqlalchemy.sql.sqltypes.NVARCHAR)):
            column_conditions = or_(column.contains(sanitize_input(query)), column.ilike(f"%{sanitize_input(query)}%"))
            conditions.append(column_conditions)
    if conditions:
        stmt = stmt.where(and_(*conditions))
    results = db.execute(stmt).fetchall()
    column_names = [column.name for column in table.columns]
    compiled_stmt = stmt.compile(compile_kwargs={"literal_binds": True})
    logging.info(f"Executed SQL: {compiled_stmt}")
    return templates.TemplateResponse("search_results.html", {"request": request, "table_name": table_name, "results": results, "column_names": column_names})

@app.get("/table/{table_name}/export", response_class=StreamingResponse)
def export_table(request: Request, table_name: str, db: Session = Depends(get_db)):
    table = Table(table_name, metadata, autoload_with=engine)
    stmt = select(table)
    results = db.execute(stmt).fetchall()

    # 构建CSV文件内容
    output = io.StringIO()
    writer = csv.writer(output)

    # 写入表头
    writer.writerow([column.name for column in table.columns])

    # 写入数据行
    for row in results:
        writer.writerow(row)

    # 设置响应头
    headers = {
        'Content-Disposition': f'attachment; filename="{table_name}.csv"',
        'Content-Type': 'text/csv'
    }

    # 返回CSV文件
    output.seek(0)
    return StreamingResponse(output.getvalue().encode(), headers=headers)

# 输入验证和过滤函数
import re

def sanitize_input(input_str):
    """
    验证和过滤用户输入,防止注入攻击等安全风险。
    """
    # 去除多余的空白字符
    input_str = input_str.strip()

    # 防止SQL注入
    input_str = re.sub(r"['\";]", "", input_str)

    # 防止XSS攻击
    input_str = re.sub(r"<script>.*?</script>", "", input_str, flags=re.IGNORECASE)

    # 其他安全检查...

    return input_str

# Jinja2 自定义过滤器
import hashlib
from functools import lru_cache

@lru_cache(maxsize=128)
def hash_value(value, salt):
    """
    使用哈希函数和Salt值对字符串进行哈希加密,并缓存结果。
    """
    value = str(value)
    hash_obj = hashlib.sha256()
    hash_obj.update(value.encode('utf-8'))
    hash_obj.update(salt.encode('utf-8'))
    return hash_obj.hexdigest()

# 注册Jinja2过滤器
templates.env.filters['hash_value'] = hash_value
