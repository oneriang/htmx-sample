# app/main.py

from fastapi import FastAPI, Depends, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from typing import List, Dict
from . import models, crud, database, schemas
from fastapi.requests import Request

app = FastAPI()
templates = Jinja2Templates(directory="app/templates")

def get_db():
    db = database.SessionLocal()
    try:
        yield db
    finally:
        db.close()

# @app.get("/")
# def read_root():
#     return {"Hello": "World"}

@app.get("/", response_class=HTMLResponse)
def read_root(request: Request, db: Session = Depends(get_db)):
    table_names = crud.get_table_names(db)
    return templates.TemplateResponse("index.html", {"request": request, "table_names": table_names})

@app.get("/tables/", response_model=List[str])
def read_tables(db: Session = Depends(get_db)):
    return crud.get_table_names(db)

@app.get("/crud", response_class=HTMLResponse)
def crud_ui(request: Request, table_name: str, skip: int = 0, limit: int = 10, db: Session = Depends(get_db)):
    columns = crud.get_columns(db, table_name)
    # print(columns)
    items = crud.get_items(db, table_name, skip, limit)
    # print(items)
    return templates.TemplateResponse("crud.html", {"request": request, "table_name": table_name, "columns": columns, "items": items})

    # total_items = get_item_count(db, table_name)
    # return templates.TemplateResponse("crud.html", {"request": request, "table_name": table_name, "columns": columns, "items": items, "total_items": total_items, "skip": skip, "limit": limit})

@app.post("/{table_name}/", response_model=schemas.Item)
def create_item(table_name: str, data: Dict, db: Session = Depends(get_db)):
    item = crud.create_item(db, table_name, data)
    return item

@app.put("/{table_name}/{item_id}", response_model=schemas.Item)
def update_item(table_name: str, item_id: int, data: Dict, db: Session = Depends(get_db)):
    item = crud.update_item(db, table_name, item_id, data)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    return item

@app.delete("/{table_name}/{item_id}")
def delete_item(table_name: str, item_id: int, db: Session = Depends(get_db)):
    item = crud.delete_item(db, table_name, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    return {"detail": "Item deleted"}
