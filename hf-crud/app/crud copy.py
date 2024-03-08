from sqlalchemy import inspect
from sqlalchemy.orm import Session
from . import models

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
            "type": column_info["type"],
            "nullable": column_info["nullable"],
            "default": column_info["default"],
            "primary_key": column_info["primary_key"],
        }
        columns.append(column)

    return columns

def get_item_by_id(db: Session, item_id: int):
    return db.query(models.Item).filter(models.Item.id == item_id).first()

def create_item(db: Session, name: str, description: str):
    item = models.Item(name=name, description=description)
    db.add(item)
    db.commit()
    db.refresh(item)
    return item

def update_item(db: Session, item_id: int, name: str, description: str):
    item = db.query(models.Item).filter(models.Item.id == item_id).first()
    if not item:
        return None

    item.name = name
    item.description = description
    db.commit()
    return item

def delete_item(db: Session, item_id: int):
    item = db.query(models.Item).filter(models.Item.id == item_id).first()
    if not item:
        return None

    db.delete(item)
    db.commit()
    return item
