# main.py
from fastapi import FastAPI, Request, Form, HTTPException
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from sqlalchemy import create_engine, MetaData, Table, select, insert, update, delete, inspect
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import SQLAlchemyError
from typing import List, Dict, Any

app = FastAPI()
templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")

# Database connection configuration
DATABASE_URL = "sqlite:///./Chinook.db"  # 使用您自己的数据库 URL
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
metadata = MetaData()

# 反射现有的数据库表
metadata.reflect(bind=engine)

def get_primary_key(table):
    return next(iter(table.primary_key.columns)).name

def get_table_names():
    inspector = inspect(engine)
    return inspector.get_table_names()

@app.get("/")
async def read_root(request: Request):
    tables = get_table_names()
    return templates.TemplateResponse("all_in_one.html", {"request": request, "tables": tables}, block_name="index")

@app.get("/table/{table_name}")
async def read_table(request: Request, table_name: str):
    if table_name not in metadata.tables:
        raise HTTPException(status_code=404, detail="Table not found")
    
    table = metadata.tables[table_name]
    primary_key = get_primary_key(table)
    
    with SessionLocal() as session:
        result = session.execute(select(table)).fetchall()
        columns = table.columns.keys()
        
    return templates.TemplateResponse("all_in_one.html", {
        "request": request,
        "table_name": table_name,
        "columns": columns,
        "rows": result,
        "primary_key": primary_key
    }, block_name="table")

@app.get("/create/{table_name}")
async def create_form(request: Request, table_name: str):
    if table_name not in metadata.tables:
        raise HTTPException(status_code=404, detail="Table not found")
    
    table = metadata.tables[table_name]
    columns = [col.name for col in table.columns if col.name != get_primary_key(table)]
    return templates.TemplateResponse("all_in_one.html", {"request": request, "table_name": table_name, "columns": columns}, block_name="create_form")

@app.post("/create/{table_name}")
async def create_item(table_name: str, data: Dict[str, Any] = Form(...)):
    if table_name not in metadata.tables:
        raise HTTPException(status_code=404, detail="Table not found")
    
    table = metadata.tables[table_name]
    
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
    print(table_name)
    if table_name not in metadata.tables:
        raise HTTPException(status_code=404, detail="Table not found")
    
    table = metadata.tables[table_name]
    primary_key = get_primary_key(table)
    
    with SessionLocal() as session:
        stmt = select(table).where(getattr(table.c, primary_key) == id)
        result = session.execute(stmt).fetchone()._asdict()

    print(result)
    
    if result:
        return templates.TemplateResponse("all_in_one.html", {
            "request": request,
            "table_name": table_name,
            "id": id,
            "item": dict(result),
            "primary_key": primary_key
        }, block_name="edit_form")
    raise HTTPException(status_code=404, detail="Item not found")

@app.post("/edit/{table_name}/{id}")
async def edit_item(table_name: str, id: str, data: Dict[str, Any] = Form(...)):
    if table_name not in metadata.tables:
        raise HTTPException(status_code=404, detail="Table not found")
    
    table = metadata.tables[table_name]
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
    if table_name not in metadata.tables:
        raise HTTPException(status_code=404, detail="Table not found")
    
    table = metadata.tables[table_name]
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