from sqlalchemy import create_engine, Table, Column, Integer, String, MetaData, ForeignKey
from sqlalchemy.orm import sessionmaker

# 创建一个数据库引擎
engine = create_engine('sqlite:///:memory:', echo=True)

# 创建一个元数据对象
metadata = MetaData()

# 定义两个表
users = Table('users', metadata,
              Column('id', Integer, primary_key=True),
              Column('name', String),
              Column('fullname', String))

addresses = Table('addresses', metadata,
                  Column('id', Integer, primary_key=True),
                  Column('user_id', None, ForeignKey('users.id')),
                  Column('email_address', String, nullable=False))

# 创建表格
metadata.create_all(engine)

# 插入一些数据
conn = engine.connect()
conn.execute(users.insert(), [
    {'name': 'John', 'fullname': 'John Doe'},
    {'name': 'Susan', 'fullname': 'Susan Johnson'},
])

conn.execute(addresses.insert(), [
    {'user_id': 1, 'email_address': 'john@example.com'},
    {'user_id': 2, 'email_address': 'susan@example.com'},
])

# 创建一个会话
Session = sessionmaker(bind=engine)
session = Session()

# 定义连接条件
join_conditions = {
    users.c.id: addresses.c.user_id
}

# Convert keys in join_conditions dictionary to string representations
join_conditions = {str(key): value for key, value in join_conditions.items()}

from sqlalchemy.orm import aliased

# Create aliases for tables
users_alias = aliased(users)
addresses_alias = aliased(addresses)

# Define join conditions using aliases
join_conditions = {
    users_alias.id: addresses_alias.user_id
}

# Perform join query
result = session.query(users, addresses).join(addresses_alias, **join_conditions).all()
## Perform join query
#result = session.query(users, addresses).join(addresses, **join_conditions).all()
## 进行join查询
#result = session.query(users, addresses).join(addresses, **join_conditions).all()

for row in result:
    print(row)