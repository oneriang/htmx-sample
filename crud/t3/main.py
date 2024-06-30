from fastapi import FastAPI, Request, Form, HTTPException, Query, Depends
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from sqlalchemy import create_engine, MetaData, Table, select, insert, update, delete, inspect, or_, func
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import SQLAlchemyError
from typing import List, Dict, Any
from math import ceil

app = FastAPI()
templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")

DATABASE_URL = "sqlite:///./Chinook.db"
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
metadata = MetaData()

metadata.reflect(bind=engine)

def get_primary_key(table):
    return next(iter(table.primary_key.columns)).name

def get_table_names():
    inspector = inspect(engine)
    return inspector.get_table_names()

def paginate(query, page, page_size, session):
    total = session.execute(query.with_only_columns([func.count()]).order_by(None)).scalar()
    items = session.execute(query.offset((page - 1) * page_size).limit(page_size)).all()
    return items, total

@app.get("/")
async def read_root(request: Request):
    tables = get_table_names()
    return templates.TemplateResponse("all_in_one.html", {"request": request, "tables": tables}, block_name="index")

@app.get("/table/{table_name}")
async def read_table(
    request: Request, 
    table_name: str, 
    page: int = Query(1, ge=1), 
    page_size: int = Query(10, ge=1, le=100),
    search: str = Query(None)
):
    if table_name not in metadata.tables:
        raise HTTPException(status_code=404, detail="Table not found")
    
    table = metadata.tables[table_name]
    primary_key = get_primary_key(table)
    
    with SessionLocal() as session:
        query = select(table)
        
        if search:
            search_conditions = [column.ilike(f"%{search}%") for column in table.columns if column.type.python_type == str]
            query = query.where(or_(*search_conditions))
        
        items, total = paginate(query, page, page_size, session)
        
        columns = table.columns.keys()
        total_pages = ceil(total / page_size)
    
    return templates.TemplateResponse("all_in_one.html", {
        "request": request,
        "table_name": table_name,
        "columns": columns,
        "rows": items,
        "primary_key": primary_key,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages,
        "total_items": total,
        "search": search or ""
    }, block_name="table")

@app.get("/create/{table_name}")
async def create_form(request: Request, table_name: str):
    if table_name not in metadata.tables:
        raise HTTPException(status_code=404, detail="Table not found")
    
    table = metadata.tables[table_name]
    columns = [col.name for col in table.columns if col.name != get_primary_key(table)]
    return templates.TemplateResponse("all_in_one.html", {"request": request, "table_name": table_name, "columns": columns}, block_name="create_form")

@app.post("/create/{table_name}")
async def create_item(table_name: str, request: Request):
    if table_name not in metadata.tables:
        raise HTTPException(status_code=404, detail="Table not found")
    
    table = metadata.tables[table_name]
    data = await request.form()
    data_dict = dict(data)
    
    try:
        with SessionLocal() as session:
            stmt = insert(table).values(**data_dict)
            session.execute(stmt)
            session.commit()
        return {"success": True, "message": "Item created successfully"}
    except SQLAlchemyError as e:
        return {"success": False, "message": str(e)}

@app.get("/edit/{table_name}/{id}")
async def edit_form(request: Request, table_name: str, id: str):
    if table_name not in metadata.tables:
        raise HTTPException(status_code=404, detail="Table not found")
    
    table = metadata.tables[table_name]
    primary_key = get_primary_key(table)
    
    with SessionLocal() as session:
        stmt = select(table).where(getattr(table.c, primary_key) == id)
        result = session.execute(stmt).fetchone()

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
async def edit_item(table_name: str, id: str, request: Request):
    if table_name not in metadata.tables:
        raise HTTPException(status_code=404, detail="Table not found")
    
    table = metadata.tables[table_name]
    primary_key = get_primary_key(table)
    data = await request.form()
    data_dict = dict(data)
    
    try:
        with SessionLocal() as session:
            stmt = update(table).where(getattr(table.c, primary_key) == id).values(**data_dict)
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
