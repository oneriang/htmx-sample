from fastapi import FastAPI, HTTPException, Request, Depends
from fastapi.responses import HTMLResponse
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
# import transaction_module  # 导入事务处理模块


app = FastAPI()

app.mount(path="/static", app=StaticFiles(directory="static"), name="static")

templates = Jinja2Templates(directory="templates")

#logging.basicConfig(level=logging.INFO)
#logging.getLogger("sqlalchemy.engine").setLevel(logging.DEBUG)

# 设置日志记录
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DATABASE_URL = "sqlite:///./Chinook.db"
#DATABASE_URL = "sqlite:///../t1/example.db"
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
    #return templates.TemplateResponse("index.html>


import json
import os
from sqlalchemy import inspect

def get_column_info(table):
    #global engine
    # 检查 JSON 文件是否存在
    if os.path.exists(f'{table.name}.json'):
        # 如果存在，则从 JSON 文件中读取列信息
        with open(f'{table.name}.json') as f:
            #return json.load(f)
            column_info = json.load(f)
            
            for c in column_info:
                if 'data_source' in c:
                    if c['data_source'] == 'countries':
                        
                        if os.path.exists('countries.json') == False:
                            # 获取 ISO 国家列表
                            countries = list(pycountry.countries)
                            
                            # 提取国家名称
                            country_names = [country.name for country in countries]
                            
                            # 写入到 JSON 文件
                            with open('countries.json', 'w') as file:
                                json.dump(country_names, file, indent=4)
                       
                        # 读取国家列表
                        with open('countries.json') as file:
                            country_list = json.load(file)
                            
                            c['form_element']['options'] = country_list
                
            return column_info
    else:
        # 7如果不存在，则从数据库中获取列信息
        #inspector = inspect(engine)
        columns = table.columns
        #inspector.get_columns(table_name)
        column_info = []
        for c in columns:
            column_info.append({
                'name': c.name,
                'label': c.name,
                'type': str(c.type),
                'required': c.nullable == False,
                'primary_key': c.primary_key,
                #'max_length': column.length
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

    total_results = None  # 初期値を設定
    
    if query is not None:
        conditions = []
        for column in table.columns:
            if isinstance(column.type, (sqlalchemy.sql.sqltypes.String, sqlalchemy.sql.sqltypes.TEXT, sqlalchemy.sql.sqltypes.NVARCHAR)):
                column_conditions = or_(column.contains(query), column.ilike(f"%{query}%"))
                conditions.append(column_conditions)
        if conditions:
            stmt = stmt.where(or_(*conditions))
            # クエリが適用された後に集計を行う
            total_results = db.query(func.count()).select_from(table).filter(*conditions).scalar()
                
    if total_results is None:  # クエリが適用されなかった場合の集計
        total_results = db.query(func.count()).select_from(table).scalar()

    if sort_column:
        if sort_order == "asc":
            stmt = stmt.order_by(asc(table.c[sort_column]))
        elif sort_order == "desc":
            stmt = stmt.order_by(desc(table.c[sort_column]))

    stmt = stmt.limit(per_page).offset((page - 1) * per_page)
    
    # 自动检测日期时间列并进行格式化
    for column in table.columns:
        #print(column.type)
        if isinstance(column.type, (sqlalchemy.sql.sqltypes.DateTime)):
            stmt = stmt.column(func.strftime('%Y-%m-%dT%H:%M', column))
        
    results = db.execute(stmt).mappings().all()
    primary_key = next((column.name for column in table.columns if column.primary_key), None)
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
        "sort_order": sort_order
    })

@app.post("/table/{table_name}/insert", response_class=HTMLResponse)
async def insert_record(request: Request, table_name: str, db: Session = Depends(get_db)):
    form_data = await request.form()
    data_dict = {}
    for key, value in form_data.items():
        data_dict[key] = value

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

    # 读取JSON文件
    with open(f'{table_name}.json', 'r') as file:
        data_json = json.load(file)

    # 创建一个空字典
    column_dict = {}

    # 遍历JSON数据，并将name属性作为key，对应的JSON数据作为value存入字典
    for item in data_json:
        column_dict[item['name']] = item
        
    table = Table(table_name, metadata, autoload_with=engine)
    primary_key = get_primary_key(table)
    primary_key_value = form_data.get(primary_key)

    for key, value in form_data.items():
        if key != primary_key:
            if column_dict[key]['type'] == 'DATETIME':
                data_dict[key] = datetime.strptime(value, '%Y-%m-%dT%H:%M')
            else:
                data_dict[key] = value

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
        stmt = delete(table).where(getattr(table.c, primary_key) == primary_key_value)
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
            column_conditions = or_(column.contains(query), column.ilike(f"%{query}%"))
            conditions.append(column_conditions)
    if conditions:
        stmt = stmt.where(and_(*conditions))
    results = db.execute(stmt).fetchall()
    column_names = [column.name for column in table.columns]
    compiled_stmt = stmt.compile(compile_kwargs={"literal_binds": True})
    #logging.info(f"Executed SQL: {compiled_stmt}")
    return templates.TemplateResponse("search_results.html", {"request": request, "table_name": table_name, "results": results, "column_names": column_names})

@app.get("/execute_all_transactions/")
async def execute_all_transactions():
    db = SessionLocal()
    res = None
    try:
        res = execute_all_transactions()  # 调用事务处理模块的函数
    except Exception as e:
        logger.error(f"Unexpected error executing transactions: {e}")
        db.rollback()
    finally:
        db.close()
    return res
    #return {"message": "All transactions executed successfully."}


# 从 JSON 文件中加载数据的函数
def load_data_from_json():
    try:
        with open("chinook.json", "r") as file:
            return json.load(file)
    except FileNotFoundError:
        logger.error("chinook.json 文件未找到。")
        return None
    except json.JSONDecodeError:
        logger.error("解析 JSON 数据时出错。")
        return None



# 事务类，表示一个包含多个步骤的事务
class Transaction:
    """
    表示一个包含多个步骤的事务。
    """
    def __init__(self, name, steps):
        self.name = name
        self.steps = steps

# 执行单个事务步骤的函数
def execute_step(step, db):
    """
    执行事务中的单个步骤。
    """
    action = step["action"]
    print(action)
    try:
        if action == "insert":
            print(step["table"])
            # table = globals()[step["table"]]
            table = Table(step["table"], metadata, autoload_with=engine)
            print(table)
            values = step["values"]
            print(values)
            result = db.execute(table.insert().values(**values))
            return result.rowcount
        elif action == "update":
            #table = globals()[step["table"]]
            table = Table(step["table"], metadata, autoload_with=engine)
            values = step["values"]
            filters = build_filter_clauses(step.get("filter_values", []), table)
            result = db.execute(table.update().where(*filters).values(**values))
            return result.rowcount
        elif action == "delete":
            #table = globals()[step["table"]]
            table = Table(step["table"], metadata, autoload_with=engine)
            filters = build_filter_clauses(step.get("filter_values", []), table)
            result = db.execute(table.delete().where(*filters))
            return result.rowcount
        elif action == "get":
            #table = globals()[step["table"]]
            table = Table(step["table"], metadata, autoload_with=engine)
            query = build_query(step, table)
            result = db.execute(query).mappings().all()
            return result
        else:
            raise ValueError(f"不支持的操作: {action}")
    except Exception as e:
        logger.error(f"执行步骤时出错: {e}")
        raise e

# 构建过滤条件的函数
def build_filter_clauses(filter_values, table):
    """
    基于给定的过滤值构建 SQLAlchemy 过滤表达式。
    """
    filters = build_filter_expressions(filter_values, table)
    return filters

# 构建过滤表达式的函数
def build_filter_expressions(filter_values, table):
    """
    基于给定的过滤值构建 SQLAlchemy 过滤表达式。
    """
    filters = []
    for f in filter_values:
        if "type" in f:
            condition_type = f["type"]
            if condition_type == "and":
                and_items = f.get("conditions", [])
                and_filters = handle_conditions(and_items, table)
                filters.extend(and_filters)
            elif condition_type == "or":
                or_items = f.get("conditions", [])
                or_filters = handle_conditions(or_items, table)
                filters.append(or_(*or_filters))
            else:
                raise ValueError(f"不支持的条件类型: {condition_type}")
        else:
            field = f["field"]
            operator = f["operator"]
            value = convert_value(table.c[field].type, f["value"])
            column = table.c[field]
            filters.append(handle_operator(column, operator, value))

    return filters

# 构建查询的函数
def build_query(step, table):
    """
    基于给定的步骤和表构建 SQLAlchemy 查询对象。
    """
    query = None
    
    if step.get("fields"):
        fields = step.get("fields", ["*"])
        select_fields = []
        for f in fields:
            t = f.get("table")
            if t:
                #t = globals()[t]
                t = Table(t)
            else:
                t = table
            c = t.c[f["field"]]
            select_fields.append(c)
        query = select(*select_fields)
    else:
        query = select(table)

    join = step.get("join")
    if join:
        for j in join:
            #left_table = globals()[j["left_table"]]
            #right_table = globals()[j["right_table"]]
            left_table = Table(j["left_table"])
            right_table = Table(j["right_table"])
            join_type = j["type"]
            join_on = []
            for o in j["on"]:
                join_on.append(left_table.c[o["left_column"]] == right_table.c[o["right_column"]])
            query = query.join(right_table, and_(*join_on), isouter=join_type == "left")

    filter_values = step.get("filter_values", [])
    query = apply_filters(query, filter_values, table)

    return query

# 应用过滤条件的函数
def apply_filters(query, filter_values, table):
    """
    根据过滤值将过滤条件应用到查询中。
    """
    and_filters = build_filter_expressions(filter_values, table)
    if and_filters:
        query = query.filter(*and_filters)

    return query

# 处理条件的函数
def handle_conditions(conditions, table):
    """
    处理给定的条件并构建 SQLAlchemy 过滤表达式。
    """
    filters = []
    for condition in conditions:
        if "type" in condition:
            condition_type = condition["type"]
            if condition_type == "and":
                and_items = condition.get("conditions", [])
                and_filters = handle_conditions(and_items, table)
                filters.append(and_(*and_filters))
            elif condition_type == "or":
                or_items = condition.get("conditions", [])
                or_filters = handle_conditions(or_items, table)
                filters.append(or_(*or_filters))
            else:
                raise ValueError(f"不支持的条件类型: {condition_type}")
        else:
            field = condition["field"]
            operator = condition["operator"]
            value = convert_value(table.c[field].type, condition["value"])
            column = table.c[field]
            filters.append(handle_operator(column, operator, value))

    return filters

# 转换值类型的函数
def convert_value(column_type, value):
    """
    根据列类型将值转换为适当的数据类型。
    """
    if column_type.python_type == int:
        return int(value)
    elif column_type.python_type == float:
        return float(value)
    else:
        return value

# 处理操作符的函数
def handle_operator(column, operator, value):
    """
    处理不同的操作符并返回相应的过滤表达式。
    """
    if operator == "eq":
        return column == value
    elif operator == "ne":
        return column != value
    elif operator == "lt":
        return column < value
    elif operator == "gt":
        return column > value
    elif operator == "le":
        return column <= value
    elif operator == "ge":
        return column >= value
    elif operator == "like":
        return column.like(value)
    elif operator == "ilike":
        return column.ilike(value)
    elif operator == "in":
        return column.in_(value)
    elif operator == "not_in":
        return ~column.in_(value)
    elif operator == "is_null":
        return column.is_(None)
    elif operator == "is_not_null":
        return column.isnot(None)
    else:
        raise ValueError(f"不支持的操作符: {operator}")

# FastAPI 路由，用于执行所有事务
# @app.get("/execute_all_transactions/")
def execute_all_transactions():
    # 加载数据
    data = load_data_from_json()
    # get_db()
    # if db:
    #     pass
    # else:
    #     db = SessionLocal()
    db = SessionLocal()
    try:
        if data:
            with db.begin():
                for transaction_data in data["transactions"]:
                    transaction = Transaction(**transaction_data)
                    for step in transaction.steps:
                        try:
                            #print("a")
                            #print(db)
                            result = execute_step(step, db)
                            logger.info(result)
                        except Exception as e:
                            logger.error(f"执行步骤时出错: {e}")
                            raise e
        else:
            logger.error("在 data.json 文件中未找到数据。")
    except SQLAlchemyError as e:
        logger.error(f"执行事务时出错: {e}")
        db.rollback()
    except Exception as e:
        logger.error(f"执行事务时发生意外错误: {e}")
        #print(str(e.orig) + " for parameters" + str(e.params))
        db.rollback()
    finally:
        db.close()
    #print("所有事务已成功执行。")
    #return {"message": "所有事务已成功执行。"}
    return result

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

