# app/crud.py

from sqlalchemy import inspect
from sqlalchemy.orm import Session
from . import models, database
from app.models import create_table_class
from app.database import engine
from datetime import datetime

def get_table_names(db: Session):
    inspector = inspect(db.bind)
    return inspector.get_table_names()

def get_columns(db: Session, table_name: str):
    inspector = inspect(db.bind)
    column_infos = inspector.get_columns(table_name)

    columns = []
    for column_info in column_infos:
        column = {
            "name": column_info["name"],
            "type": str(column_info["type"]),
            "nullable": column_info["nullable"],
            "default": column_info["default"],
            "primary_key": column_info["primary_key"],
        }
        print(column)
        columns.append(column)

    return columns

def get_items(db: Session, table_name: str, limit: int, offset: int):
    table_class = create_table_class(table_name, engine)
    query = db.query(table_class)
    total_items = query.count()
    items = query.limit(limit).offset(offset).all()
    return items, total_items
    
def create_item(db: Session, table_name: str, data: dict):
    # 创建表对应的类
    table_class = create_table_class(table_name, engine)

    # 创建新项目
    item = table_class(**data)
    db.add(item)
    db.commit()
    db.refresh(item)

    return item

def get_primary_key_value(data: dict, columns: dict):
    """
    Get the primary key column name and value from the data dictionary.
    """
    for column in columns:
        if column["primary_key"]:
            column_name = column["name"]
            column_value = data.get(column_name)
            if column_value is not None:
                return column_name, column_value
    raise ValueError("Primary key column not found in the data")

# def update_item(db: Session, table_name: str, data: dict):
#     # 获取表的列信息
#     columns = get_columns(db, table_name)
    
#     # 获取主键列的名称和值
#     primary_key_column, primary_key_value = get_primary_key_value(data, columns)

#     # 创建表对应的类
#     table_class = create_table_class(table_name, engine)

#     # 更新项目
#     item = db.query(table_class).filter(getattr(table_class, primary_key_column) == primary_key_value).first()
#     if item:
#         for key, value in data.items():
#             setattr(item, key, value)
#         db.commit()
#     return item
def update_item(db: Session, table_name: str, data: dict):
    print("update_item")
    print(data)

    # 获取表的列信息
    columns = get_columns(db, table_name)

    
    # 获取主键列的名称和值
    primary_key_column, primary_key_value = get_primary_key_value(data, columns)

    # 创建表对应的类
    table_class = create_table_class(table_name, engine)

    # 更新项目
    item = db.query(table_class).filter(getattr(table_class, primary_key_column) == primary_key_value).first()
    if item:
        for key, value in data.items():
            # 获取字段类型
            column_type = next((column["type"] for column in columns if column["name"] == key), None)
            if column_type:
                # 根据字段类型进行值的转换
                if column_type.startswith("VARCHAR") or column_type.startswith("CHAR") or column_type.startswith("TEXT"):
                    # 字符串类型
                    setattr(item, key, str(value))
                elif column_type.startswith("INT") or column_type.startswith("NUMERIC") or column_type.startswith("FLOAT"):
                    # 整数或浮点数类型
                    setattr(item, key, int(value))
                elif column_type.startswith("DATE") or column_type.startswith("TIME"):
                    # 日期或时间类型
                    setattr(item, key, datetime.strptime(value, "%Y-%m-%d"))
                # 在此添加其他类型的转换，例如布尔值等
            else:
                # 默认情况下直接赋值
                setattr(item, key, value)
        db.commit()
    return item

def delete_item(db: Session, table_name: str, data: dict):
    # 获取表的列信息
    columns = get_columns(db, table_name)
    
    # 获取主键列的名称和值
    primary_key_column, primary_key_value = get_primary_key_value(data, columns)

    # 创建表对应的类
    table_class = create_table_class(table_name, engine)

    # 删除项目
    item = db.query(table_class).filter(getattr(table_class, primary_key_column) == primary_key_value).first()
    if item:
        db.delete(item)
        db.commit()
