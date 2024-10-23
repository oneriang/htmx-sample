
from sqlalchemy import create_engine, text

engine = create_engine("sqlite:///Chinook.db")

def execute_query(query, params=None):
    with engine.connect() as connection:
        result = connection.execute(text(query), params)
        return result.fetchall()
