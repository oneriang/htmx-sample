# app/models.py

from sqlalchemy import Column, Integer, String, MetaData
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Table

metadata = MetaData()
Base = declarative_base(metadata=metadata)

# def create_table_class(table_name):
#     print('metadata')
#     print(metadata)
#     table = metadata.tables[table_name]
#     columns = {}

#     for column in table.columns:
#         columns[column.name] = column.type

#     class_name = table_name.capitalize()
#     table_class = type(class_name, (Base,), columns)

#     return table_class

def create_table_class(table_name, engine):
    # 获取表对应的 Table 对象
    table = Table(table_name, Base.metadata, autoload_with=engine)

    # 创建表对应的类
    class_name = table_name.capitalize()
    table_class = type(class_name, (Base,), {"__table__": table})

    return table_class