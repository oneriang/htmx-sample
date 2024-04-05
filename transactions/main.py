from fastapi import FastAPI
from pydantic import BaseModel
import sqlite3
import json

app = FastAPI()

class Step(BaseModel):
    action: str
    table: str
    values: dict

class Transaction(BaseModel):
    name: str
    steps: list[Step]

ref = {}

def execute_step(step: Step):
    conn = sqlite3.connect('example.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    print(step)
    if step.action == "insert":
        columns = ', '.join(step.values.keys())
        print(columns)
        placeholders = ', '.join(['?' for _ in step.values])
        print(placeholders)
        sql = f"INSERT INTO {step.table} ({columns}) VALUES ({placeholders})"
        print(sql)
        print(step.values.values())
        print(list(step.values.values()))
        cursor.execute(sql, list(step.values.values()))
        conn.commit()
    elif step.action == "get_last_insert_id":
        print("get_last_insert_id")
        cursor.execute(f"SELECT * from {step.table} ORDER BY ROWID DESC LIMIT 1")
        result = cursor.fetchone()
        print(result)
        ref["user_id"] = result[0]
        print("------------")
        print(result[0])
        print("------------")
        print(ref)
        #return result[0] if result else None

    conn.close()

def create_db_and_tables():
    conn = sqlite3.connect('example.db')
    cursor = conn.cursor()

    cursor.execute('''DROP TABLE IF EXISTS users ''')
    # 创建 users 表
    cursor.execute('''CREATE TABLE IF NOT EXISTS users (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        username TEXT,
                        email TEXT)''')
                        
    cursor.execute('''DROP TABLE IF EXISTS posts ''')
    # 创建 posts 表
    cursor.execute('''CREATE TABLE IF NOT EXISTS posts (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        title TEXT,
                        content TEXT,
                        user_id INTEGER,
                        FOREIGN KEY (user_id) REFERENCES users(id))''')

    conn.commit()
    conn.close()

def load_transactions_from_json():
    with open("transactions.json", "r") as file:
        return json.load(file)

create_db_and_tables()
transactions_data = load_transactions_from_json()

@app.get("/execute_all_transactions/")
async def execute_all_transactions():
    for transaction_data in transactions_data["transactions"]:
        transaction = Transaction(**transaction_data)
        for step in transaction.steps:
            execute_step(step)
    return {"message": "All transactions executed successfully."}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=9000)
