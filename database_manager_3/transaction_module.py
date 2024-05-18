from fastapi import FastAPI
from sqlalchemy import create_engine, MetaData, Table, Column, Integer, String, ForeignKey
from sqlalchemy.orm import sessionmaker
from sqlalchemy.sql import select, and_, or_
from sqlalchemy.exc import SQLAlchemyError
import json
import logging

# 设置日志记录
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 常量定义
SQLALCHEMY_DATABASE_URL = "sqlite:///../t1/example.db"

app = FastAPI()

# 创建数据库连接
engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 创建 metadata
metadata = MetaData()

# 定义数据库表
users = Table(
    "users",
    metadata,
    Column("id", Integer, primary_key=True, index=True),
    Column("username", String, index=True),
    Column("email", String, index=True),
)

posts = Table(
    "posts",
    metadata,
    Column("id", Integer, primary_key=True, index=True),
    Column("title", String),
    Column("content", String),
    Column("user_id", Integer, ForeignKey("users.id")),
)

# 创建数据库表
metadata.create_all(bind=engine)

# 从 JSON 文件中加载数据
def load_data_from_json():
    try:
        with open("data.json", "r") as file:
            return json.load(file)
    except FileNotFoundError:
        logger.error("data.json file not found.")
        return None
    except json.JSONDecodeError:
        logger.error("Error decoding JSON data.")
        return None

data = load_data_from_json()

class Transaction:
    """
    Represents a transaction that consists of a sequence of steps.
    """
    def __init__(self, name, steps):
        self.name = name
        self.steps = steps

def execute_step(step, db):
    """
    Execute a single step in the transaction.
    """
    action = step["action"]
    try:
        if action == "insert":
            table = globals()[step["table"]]
            values = step["values"]
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
            raise ValueError(f"Unsupported action: {action}")
    except Exception as e:
        logger.error(f"Error executing step: {e}")
        raise e

def build_filter_clauses(filter_values, table):
    """
    Build SQLAlchemy filter expressions based on the given filter_values.
    """
    filters = build_filter_expressions(filter_values, table)
    return filters

def build_filter_expressions(filter_values, table):
    """
    Build SQLAlchemy filter expressions based on the given filter_values.
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
                raise ValueError(f"Unsupported condition type: {condition_type}")
        else:
            field = f["field"]
            operator = f["operator"]
            value = convert_value(table.c[field].type, f["value"])
            column = table.c[field]
            filters.append(handle_operator(column, operator, value))

    return filters

def build_query(step, table):
    """
    Build a SQLAlchemy query object based on the given step and table.
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

def apply_filters(query, filter_values, table):
    """
    Apply filters to the given query based on the filter_values.
    """
    and_filters = build_filter_expressions(filter_values, table)
    if and_filters:
        query = query.filter(*and_filters)

    return query

def handle_conditions(conditions, table):
    """
    Handle the given conditions and construct SQLAlchemy filter expressions.
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
                raise ValueError(f"Unsupported condition type: {condition_type}")
        else:
            field = condition["field"]
            operator = condition["operator"]
            value = convert_value(table.c[field].type, condition["value"])
            column = table.c[field]
            filters.append(handle_operator(column, operator, value))

    return filters

def convert_value(column_type, value):
    """
    Convert the value to the appropriate data type based on the column type.
    """
    if column_type.python_type == int:
        return int(value)
    elif column_type.python_type == float:
        return float(value)
    else:
        return value

def handle_operator(column, operator, value):
    """
    Handle different operators and return the corresponding filter expression.
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
        raise ValueError(f"Unsupported operator: {operator}")

@app.get("/execute_all_transactions/")
async def execute_all_transactions(db):
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
                            result = execute_step(step, db)
                            logger.info(result)
                        except Exception as e:
                            logger.error(f"Error executing step: {e}")
                            raise e
        else:
            logger.error("No data found in data.json file.")
    except SQLAlchemyError as e:
        logger.error(f"Error executing transactions: {e}")
        db.rollback()
    except Exception as e:
        logger.error(f"Unexpected error executing transactions: {e}")
        db.rollback()
    finally:
        db.close()

    return {"message": "All transactions executed successfully."}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8082)
