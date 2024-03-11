# app/crud.py

from sqlalchemy import inspect
from sqlalchemy.orm import Session
from . import models, database
from app.models import create_table_class
from app.database import engine

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

def update_item(db: Session, table_name: str, item_id: int, data: dict):
    # 创建表对应的类
    table_class = create_table_class(table_name, engine)

    # 更新项目
    item = db.query(table_class).filter(table_class.id == item_id).first()
    for key, value in data.items():
        setattr(item, key, value)
    db.commit()

    return item

def delete_item(db: Session, table_name: str, item_id: int):
    # 创建表对应的类
    table_class = create_table_class(table_name, engine)

    # 删除项目
    item = db.query(table_class).filter(table_class.id == item_id).first()
    if item:
        db.delete(item)
        db.commit()
