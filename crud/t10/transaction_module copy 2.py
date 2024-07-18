from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy import create_engine, MetaData, Table, select, and_, or_
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import SQLAlchemyError
import json
import logging
from typing import List, Dict, Any, Union
from contextlib import contextmanager

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

@contextmanager
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

data = load_data_from_json()

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

def convert_value(column_type: Any, value: Any) -> Any:
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
        with db.begin():
            for transaction_data in data.get("transactions", []):
                transaction = Transaction(**transaction_data)
                for step in transaction.steps:
                    result = execute_step(step, db)
                    logger.info(f"步骤执行结果: {result}")
        return {"message": "所有事务已成功执行。"}
    except SQLAlchemyError as e:
        logger.error(f"执行事务时出错: {e}")
        raise HTTPException(status_code=500, detail="数据库错误")
    except Exception as e:
        logger.error(f"执行事务时发生意外错误: {e}")
        raise HTTPException(status_code=500, detail="内部服务器错误")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8082)