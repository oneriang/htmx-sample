from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy import create_engine, MetaData, Table, select, and_, or_
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import SQLAlchemyError
import json
import logging
from typing import List, Dict, Any, Union

# 设置日志记录
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 定义数据库 URL 常量
SQLALCHEMY_DATABASE_URL = "sqlite:///./Chinook.db"

# 创建 FastAPI 应用实例
app = FastAPI()

# 创建数据库连接引擎
engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 创建 Metadata 实例
metadata = MetaData()

# 创建数据库表
metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def load_data_from_json(filename: str = "chinook.json") -> Dict[str, Any]:
    try:
        with open(filename, "r") as file:
            return json.load(file)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        logger.error(f"加载 JSON 数据时出错: {e}")
        return {}

# data = load_data_from_json()

class Transaction:
    def __init__(self, name: str, steps: List[Dict[str, Any]]):
        self.name = name
        self.steps = steps

def execute_step(step: Dict[str, Any], db: SessionLocal) -> Any:
    action = step["action"]
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
            return result
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
    query = select(*[table.c[f["field"]] for f in step.get("fields", [{"field": "*"}])])
    
    join = step.get("join")
    if join:
        for j in join:
            left_table = Table(j["left_table"], metadata, autoload_with=engine)
            right_table = Table(j["right_table"], metadata, autoload_with=engine)
            join_on = [left_table.c[o["left_column"]] == right_table.c[o["right_column"]] for o in j["on"]]
            query = query.join(right_table, and_(*join_on), isouter=j["type"] == "left")

    filter_values = step.get("filter_values", [])
    filters = build_filter_expressions(filter_values, table)
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

    if isinstance(column_type, BLOB):
        if isinstance(value, str):
            return value.encode('utf-8')
        elif isinstance(value, bytes):
            return value
        else:
            raise ValueError(f"无法将 {type(value)} 转换为 BLOB 类型")

    elif isinstance(column_type, Date):
        if isinstance(value, str):
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
            for fmt in ('%Y-%m-%d %H:%M:%S', '%d-%m-%Y %H:%M:%S', '%Y-%m-%d %H:%M', '%d-%m-%Y %H:%M'):
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

@app.get("/execute_all_transactions/")
def execute_all_transactions(db: SessionLocal = Depends(get_db)):
    try:
        data = load_data_from_json()
        for transaction_data in data.get("transactions", []):
            transaction = Transaction(**transaction_data)
            for step in transaction.steps:
                result = execute_step(step, db)
                logger.info(f"步骤执行结果: {result}")
        db.commit()
        return {"message": "所有事务已成功执行。"}
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"执行事务时出错: {e}")
        raise HTTPException(status_code=500, detail="数据库错误")
    except Exception as e:
        db.rollback()
        logger.error(f"执行事务时发生意外错误: {e}")
        raise HTTPException(status_code=500, detail="内部服务器错误")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8082)