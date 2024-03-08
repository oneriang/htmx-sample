from fastapi import FastAPI, Depends, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from typing import List
from . import models, crud, database, schemas

app = FastAPI()
templates = Jinja2Templates(directory="app/templates")

def get_db():
    db = database.SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.get("/")
def read_root():
    return {"Hello": "World"}

@app.get("/tables/", response_model=List[str])
def read_tables(db: Session = Depends(get_db)):
    return crud.get_table_names(db)

@app.get("/crud/{table_name}", response_class=HTMLResponse)
def crud_ui(table_name: str, db: Session = Depends(get_db)):
    columns = crud.get_columns(db, table_name)
    return templates.TemplateResponse("crud.html", {"request": None, "table_name": table_name, "columns": columns})
