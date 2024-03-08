# app/models.py

from sqlalchemy import Column, Integer, String, MetaData
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import registry

mapper_registry = registry()
Base = declarative_base(registry=mapper_registry)
metadata = MetaData()

def create_table_class(table_name):
    table = metadata.tables[table_name]
    columns = {}

    for column in table.columns:
        columns[column.name] = column.type

    class_name = table_name.capitalize()
    table_class = type(class_name, (Base,), columns)
    mapper_registry.map_imperatively(table_class, table)

    return table_class
