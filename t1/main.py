from fastapi import FastAPI
from sqlalchemy import create_engine, MetaData, Table, Column, Integer, String, ForeignKey
from sqlalchemy.orm import sessionmaker
from sqlalchemy.sql import select, and_, or_
import json

app = FastAPI()

# 创建数据库连接
# データベース接続を作成する
# 데이터베이스 연결 생성
SQLALCHEMY_DATABASE_URL = "sqlite:///./example.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 创建 metadata
# メタデータを作成する
# 메타데이터 생성
metadata = MetaData()

# 定义 users 表
# usersテーブルを定義する
# users 테이블 정의
users = Table(
    "users",
    metadata,
    Column("id", Integer, primary_key=True, index=True),
    Column("username", String, index=True),
    Column("email", String, index=True),
)

# 定义 posts 表
# postsテーブルを定義する
# posts 테이블 정의
posts = Table(
    "posts",
    metadata,
    Column("id", Integer, primary_key=True, index=True),
    Column("title", String),
    Column("content", String),
    Column("user_id", Integer, ForeignKey("users.id")),
)

# 创建数据库表
# データベーステーブルを作成する
# 데이터베이스 테이블 생성
metadata.create_all(bind=engine)

# 从 JSON 文件中加载数据
# JSONファイルからデータをロードする
# JSON 파일에서 데이터 로드
def load_data_from_json():
    with open("data.json", "r") as file:
        return json.load(file)

data = load_data_from_json()

class Transaction:
    """
    Represents a transaction that consists of a sequence of steps.
    """
    # 表示由一系列步骤组成的事务。
    # トランザクションは、一連のステップで構成されています。
    # 거래는 일련의 단계로 구성됩니다.
    def __init__(self, name, steps):
        self.name = name
        self.steps = steps

def execute_step(step, db):
    """
    Execute a single step in the transaction.

    Args:
        step (dict): A dictionary representing the step to be executed.
        db (Session): The SQLAlchemy database session.

    Returns:
        list: A list of result mappings if the step is a "get" action.

    Raises:
        ValueError: If the action specified in the step is not supported.
    """
    # 执行事务中的单个步骤。
    # トランザクションの単一ステップを実行します。
    # 트랜잭션의 단일 단계를 실행합니다.

    action = step["action"]
    if action == "insert":
        table = globals()[step["table"]]
        values = step["values"]
        db.execute(table.insert().values(**values))
    elif action == "get":
        table = globals()[step["table"]]
        query = build_query(step, table)
        result = db.execute(query).mappings().all()
        return result
    else:
        raise ValueError(f"Unsupported action: {action}")

def build_query(step, table):
    """
    Build a SQLAlchemy query object based on the given step and table.

    Args:
        step (dict): A dictionary representing the step to be executed.
        table (Table): The SQLAlchemy table object.

    Returns:
        Query: The constructed SQLAlchemy query object.
    """
    # 根据给定的步骤和表构建 SQLAlchemy 查询对象。
    # 与えられたステップとテーブルに基づいて SQLAlchemy クエリオブジェクトを構築します。
    # 주어진 단계와 테이블을 기반으로 SQLAlchemy 쿼리 개체를 작성합니다.

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

    Args:
        query (Query): The SQLAlchemy query object to be filtered.
        filter_values (list): A list of filter dictionaries.
        table (Table): The SQLAlchemy table object.

    Returns:
        Query: The filtered SQLAlchemy query object.
    """
    # 根据 filter_values 对给定的查询应用过滤器。
    # filter_valuesに基づいて、与えられたクエリにフィルターを適用します。
    # filter_values를 기반으로 주어진 쿼리에 필터를 적용합니다.

    and_filters = []
    for f in filter_values:
        if "type" in f:
            condition_type = f["type"]
            if condition_type == "and":
                and_items = f.get("conditions", [])
                and_filters.extend(handle_conditions(and_items, table))
            elif condition_type == "or":
                or_items = f.get("conditions", [])
                or_filters = handle_conditions(or_items, table)
                and_filters.append(or_(*or_filters))
            else:
                raise ValueError(f"Unsupported condition type: {condition_type}")
        else:
            raise ValueError("Condition type is not specified.")

    if and_filters:
        query = query.filter(*and_filters)

    return query

def handle_conditions(conditions, table):
    """
    Handle the given conditions and construct SQLAlchemy filter expressions.

    Args:
        conditions (list): A list of condition dictionaries.
        table (Table): The SQLAlchemy table object.

    Returns:
        list: A list of SQLAlchemy filter expressions.
    """
    # 处理给定的条件，并构建 SQLAlchemy 过滤器表达式。
    # 与えられた条件を処理し、SQLAlchemyフィルター式を構築します。
    # 주어진 조건을 처리하고 SQLAlchemy 필터 식을 작성합니다.

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
    # 根据列类型将值转换为适当的数据类型。
    # カラムの種類に基づいて値を適切なデータ型に変換します。
    # 열 유형을 기반으로 값을 적절한 데이터 유형으로 변환합니다.
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
    # 处理不同的运算符并返回相应的过滤器表达式。
    # 異なる演算子を処理し、対応するフィルター式を返します。
    # 다른 연산자를 처리하고 해당 필터 식을 반환합니다.
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
async def execute_all_transactions():
    db = SessionLocal()
    try:
        for transaction_data in data["transactions"]:
            transaction = Transaction(**transaction_data)
            for step in transaction.steps:
                try:
                    result = execute_step(step, db)
                    print(result)  # 在控制台输出查询结果，方便调试
                    # コンソールに検索結果を出力して、デバッグを容易にします。
                    # 콘솔에 검색 결과를 출력하여 디버깅을 용이하게 합니다.
                except Exception as e:
                    print(f"Error executing step: {e}")
    finally:
        db.close()

    return {"message": "All transactions executed successfully."}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)