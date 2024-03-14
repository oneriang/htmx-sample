# main.py

from fastapi import FastAPI, Depends, HTTPException, Form, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Dict
from . import models, crud, database

app = FastAPI()
templates = Jinja2Templates(directory="app/templates")

def get_db():
    db = database.SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.get("/", response_class=HTMLResponse)
def read_root(request: Request, db: Session = Depends(get_db)):
    table_names = crud.get_table_names(db)
    return templates.TemplateResponse("index.html", {"request": request, "table_names": table_names})

@app.get("/tables/", response_model=List[str])
def read_tables(db: Session = Depends(get_db)):
    return crud.get_table_names(db)


from fastapi.responses import HTMLResponse
from fastapi import Query

@app.get("/crud/{table_name}", response_class=HTMLResponse)
def search_items(request: Request, table_name: str, search_key: str = "", limit: int = 10, offset: int = 0, sort_column: str = None, sort_order: str = "asc", db: Session = Depends(get_db)):
    items, total_items = crud.search_items(db, table_name, search_key, limit, offset, sort_column, sort_order)
    table_columns = crud.get_columns(db, table_name)
    return templates.TemplateResponse("crud.html", 
        {"request": request, 
        "table_name": table_name, 
        "columns": table_columns, 
        "items": items, 
        "limit": limit, 
        "offset": offset, 
        "total_items": total_items, 
        "search_key": search_key,
        "sort_column": sort_column,
        "sort_order": sort_order})

@app.get("/crud", response_class=HTMLResponse)
def crud_ui(request: Request, table_name: str, limit: int = 10, offset: int = 0, sort_column: str = None, sort_order: str = "asc",  db: Session = Depends(get_db)):
    columns = crud.get_columns(db, table_name)
    items, total_items = crud.get_items(db, table_name, limit, offset, sort_column, sort_order)  # 修改这里
    return templates.TemplateResponse("crud.html", {"request": request, "table_name": table_name, "columns": columns, "items": items, "limit": limit, "offset": offset, "total_items": total_items})  # 修改这里

# @app.post("/aaa", response_class=HTMLResponse)
# def aaa(request: Request):
#     print(request)
#     print(request.query_params)
#     print(dict(request.query_params))  
#     return "<a>a</a>"

# class FormData(BaseModel):
#     data: Dict[str, str] = {}

# @app.post("/aaa/")
# async def process_form(form: FormData):
#     for key, value in form.data.items():
#         print(f"Key: {key}, Value: {value}")
#     return {"message": "Form data processed successfully"}

# @app.post("/aaa/")
# async def submit_form(data: Dict[str, str] = Form(...)):
#     for key, value in data.items():
#         print(f"{key}: {value}")
#     return {"data_received": data}

# from typing import Dict, Union, List

# @app.post("/aaa")
# async def handle_dynamic_form(email: str = Form()):
#     print(email)
#     # email = data.get("email")
#     return {"message": "Form data received successfully", "email": email}

@app.post("/aaa")
def create_item(data: dict):
    return data

@app.post("/crud/{table_name}")
def create_item(request: Request, table_name: str, data: dict, db: Session = Depends(get_db), limit: int = 10, offset: int = 0):
    print('------------------------')
    print('create')
    print(table_name)

    crud.create_item(db, table_name, data)
    return crud_ui(request, table_name, limit, offset, db)

@app.put("/crud/{table_name}", response_class=HTMLResponse)
def update_item(request: Request, table_name: str, data: dict, db: Session = Depends(get_db), limit: int = 10, offset: int = 0):
    print('------------------------')
    print('update')
    print(table_name)
    # return crud.update_item(db, table_name, data)
    item = crud.update_item(db, table_name, data)
    # table_columns = crud.get_columns(db, table_name)
    # items, total_items = crud.get_items(db, table_name, limit, offset)
    # return templates.TemplateResponse("crud.html", {"request": request, "table_name": table_name, "columns": table_columns, "items": items, "limit": limit, "offset": offset})
    return crud_ui(request, table_name, limit, offset, db)

@app.delete("/crud/{table_name}", response_class=HTMLResponse)
def delete_item(request: Request, table_name: str, data: dict, db: Session = Depends(get_db), limit: int = 10, offset: int = 0):
    print('------------------------')
    print('delete')
    # return crud.delete_item(db, table_name, data)
    crud.delete_item(db, table_name, data)
    return crud_ui(request, table_name, limit, offset, db)
