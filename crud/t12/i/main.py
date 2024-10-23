# main.py
from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError

app = FastAPI()
templates = Jinja2Templates(directory="templates")

# 创建数据库连接
engine = create_engine("sqlite:///todos.db")

# 创建todos表
with engine.connect() as conn:
    conn.execute(text("""
    CREATE TABLE IF NOT EXISTS todos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        completed BOOLEAN NOT NULL DEFAULT 0
    )
    """))

@app.get("/", response_class=HTMLResponse)
async def read_todos(request: Request):
    with engine.connect() as conn:
        result = conn.execute(text("SELECT * FROM todos"))
        todos = result.fetchall()
    return templates.TemplateResponse("index.html", {"request": request, "todos": todos})

@app.post("/add", response_class=HTMLResponse)
async def add_todo(request: Request, title: str = Form(...)):
    with engine.connect() as conn:
        conn.execute(text("INSERT INTO todos (title) VALUES (:title)"), {"title": title})
    
    with engine.connect() as conn:
        result = conn.execute(text("SELECT * FROM todos WHERE id = last_insert_rowid()"))
        new_todo = result.fetchone()
    
    return templates.TemplateResponse("todo_item.html", {"request": request, "todo": new_todo})

@app.put("/toggle/{todo_id}", response_class=HTMLResponse)
async def toggle_todo(request: Request, todo_id: int):
    with engine.connect() as conn:
        conn.execute(text("UPDATE todos SET completed = NOT completed WHERE id = :id"), {"id": todo_id})
        result = conn.execute(text("SELECT * FROM todos WHERE id = :id"), {"id": todo_id})
        updated_todo = result.fetchone()
    
    return templates.TemplateResponse("todo_item.html", {"request": request, "todo": updated_todo})

@app.delete("/delete/{todo_id}")
async def delete_todo(todo_id: int):
    with engine.connect() as conn:
        conn.execute(text("DELETE FROM todos WHERE id = :id"), {"id": todo_id})
    return ""
            
if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        workers=2,
        log_level="debug",
        access_log=False,
        reload_dirs=["./"]
    )
