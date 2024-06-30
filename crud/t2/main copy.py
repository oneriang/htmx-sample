# main.py
from fastapi import FastAPI, Request, Form
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from sqlalchemy import create_engine, MetaData, Table, select, insert, update, delete
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import SQLAlchemyError
from typing import List, Dict, Any

app = FastAPI()
templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")

# 数据库连接配置
DATABASE_URL = "sqlite:///./test.db"  # 使用您自己的数据库 URL
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
metadata = MetaData()

def get_primary_key(table):
    return [c.name for c in table.primary_key][0]

@app.get("/")
async def read_root(request: Request):
    tables = metadata.tables.keys()
    return templates.TemplateResponse("index.html", {"request": request, "tables": tables})

@app.get("/table/{table_name}")
async def read_table(request: Request, table_name: str):
    table = Table(table_name, metadata, autoload_with=engine)
    primary_key = get_primary_key(table)
    
    with SessionLocal() as session:
        result = session.execute(select(table)).fetchall()
        columns = table.columns.keys()
        
    return templates.TemplateResponse("table.html", {
        "request": request,
        "table_name": table_name,
        "columns": columns,
        "rows": result,
        "primary_key": primary_key
    })

@app.get("/create/{table_name}")
async def create_form(request: Request, table_name: str):
    table = Table(table_name, metadata, autoload_with=engine)
    columns = [col for col in table.columns.keys() if col != get_primary_key(table)]
    return templates.TemplateResponse("create_form.html", {"request": request, "table_name": table_name, "columns": columns})

@app.post("/create/{table_name}")
async def create_item(table_name: str, data: Dict[str, Any] = Form(...)):
    table = Table(table_name, metadata, autoload_with=engine)
    
    try:
        with SessionLocal() as session:
            stmt = insert(table).values(**data)
            session.execute(stmt)
            session.commit()
        return {"success": True, "message": "Item created successfully"}
    except SQLAlchemyError as e:
        return {"success": False, "message": str(e)}

@app.get("/edit/{table_name}/{id}")
async def edit_form(request: Request, table_name: str, id: str):
    table = Table(table_name, metadata, autoload_with=engine)
    primary_key = get_primary_key(table)
    
    with SessionLocal() as session:
        stmt = select(table).where(getattr(table.c, primary_key) == id)
        result = session.execute(stmt).fetchone()
    
    if result:
        return templates.TemplateResponse("edit_form.html", {
            "request": request,
            "table_name": table_name,
            "id": id,
            "item": dict(result),
            "primary_key": primary_key
        })
    return {"error": "Item not found"}

@app.post("/edit/{table_name}/{id}")
async def edit_item(table_name: str, id: str, data: Dict[str, Any] = Form(...)):
    table = Table(table_name, metadata, autoload_with=engine)
    primary_key = get_primary_key(table)
    
    try:
        with SessionLocal() as session:
            stmt = update(table).where(getattr(table.c, primary_key) == id).values(**data)
            session.execute(stmt)
            session.commit()
        return {"success": True, "message": "Item updated successfully"}
    except SQLAlchemyError as e:
        return {"success": False, "message": str(e)}

@app.post("/delete/{table_name}/{id}")
async def delete_item(table_name: str, id: str):
    table = Table(table_name, metadata, autoload_with=engine)
    primary_key = get_primary_key(table)
    
    try:
        with SessionLocal() as session:
            stmt = delete(table).where(getattr(table.c, primary_key) == id)
            session.execute(stmt)
            session.commit()
        return {"success": True, "message": "Item deleted successfully"}
    except SQLAlchemyError as e:
        return {"success": False, "message": str(e)}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)