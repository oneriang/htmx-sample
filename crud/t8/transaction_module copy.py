from fastapi import FastAPI  # 导入 FastAPI 框架，用于构建 API
from sqlalchemy import create_engine, MetaData, Table, Column, Integer, String, ForeignKey  # 导入 SQLAlchemy 相关模块
from sqlalchemy.orm import sessionmaker  # 导入 sessionmaker，用于创建数据库会话
from sqlalchemy.sql import select, and_, or_  # 导入 SQLAlchemy 的查询构建模块
from sqlalchemy.exc import SQLAlchemyError  # 导入 SQLAlchemy 的异常处理模块
import json  # 导入 json 模块，用于处理 JSON 文件
import logging  # 导入 logging 模块，用于日志记录

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

# 加载数据
data = load_data_from_json()

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
            table = globals()[step["table"]]
            values = step["values"]
            filters = build_filter_clauses(step.get("filter_values", []), table)
            result = db.execute(table.update().where(*filters).values(**values))
            return result.rowcount
        elif action == "delete":
            table = globals()[step["table"]]
            filters = build_filter_clauses(step.get("filter_values", []), table)
            result = db.execute(table.delete().where(*filters))
            return result.rowcount
        elif action == "get":
            table = globals()[step["table"]]
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
                t = globals()[t]
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
            left_table = globals()[j["left_table"]]
            right_table = globals()[j["right_table"]]
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
def execute_all_transactions(db):
    if db:
        pass
    else:
        db = SessionLocal()
    try:
        if data:
            with db.begin():
                for transaction_data in data["transactions"]:
                    transaction = Transaction(**transaction_data)
                    for step in transaction.steps:
                        try:
                            print("a")
                            print(db)
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
        db.rollback()
    finally:
        db.close()
    print("所有事务已成功执行。")
    return {"message": "所有事务已成功执行。"}

# 启动 FastAPI 应用
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8082)
