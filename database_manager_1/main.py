from fastapi import FastAPI, HTTPException, Request, Depends
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from sqlalchemy import create_engine, MetaData, Table, select, insert, update, delete, or_, and_, func, asc, desc
from sqlalchemy.orm import sessionmaker, Session
from typing import Dict
import logging

app = FastAPI()

app.mount(path="/static", app=StaticFiles(directory="static"), name="static")

templates = Jinja2Templates(directory="templates")

logging.basicConfig(level=logging.INFO)
logging.getLogger("sqlalchemy.engine").setLevel(logging.DEBUG)

DATABASE_URL = "sqlite:///./my_database.db"
engine = create_engine(DATABASE_URL, echo=True)
metadata = MetaData()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

metadata.reflect(bind=engine)
table_names = metadata.tables.keys()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request, "table_names": table_names})

@app.get("/a", response_class=HTMLResponse)
def index(request: Request):
    with open("static/a.html", "r", encoding="utf-8") as f:
        html = f.read()
    return HTMLResponse(html)
    #return templates.TemplateResponse("index.html>

@app.get("/table1/{table_name}", response_class=HTMLResponse)
def table_view1(request: Request, table_name: str, page: int = 1, per_page: int = 10, db: Session = Depends(get_db)):
    table = Table(table_name, metadata, autoload_with=engine)
    stmt = select(table)
    total_results = db.execute(select(func.count()).select_from(table)).scalar()
    stmt = stmt.limit(per_page).offset((page - 1) * per_page)
    results = db.execute(stmt).fetchall()
    column_names = [column.name for column in table.columns]
    primary_key = next((column.name for column in table.columns if column.primary_key), None)
    return templates.TemplateResponse("table_view.html", {"request": request, "table_name": table_name, "results": results, "column_names": column_names, "primary_key": primary_key, "total_results": total_results, "page": page, "per_page": per_page})

@app.get("/table/{table_name}", response_class=HTMLResponse)
def table_view(request: Request, table_name: str, page: int = 1, per_page: int = 10, sort_column: str = None, sort_order: str = None, db: Session = Depends(get_db)):
    table = Table(table_name, metadata, autoload_with=engine)
    stmt = select(table)
    total_results = db.execute(select(func.count()).select_from(table)).scalar()

    if sort_column:
        if sort_order == "asc":
            stmt = stmt.order_by(asc(table.c[sort_column]))
        elif sort_order == "desc":
            stmt = stmt.order_by(desc(table.c[sort_column]))

    stmt = stmt.limit(per_page).offset((page - 1) * per_page)
    results = db.execute(stmt).fetchall()
    column_names = [column.name for column in table.columns]
    primary_key = next((column.name for column in table.columns if column.primary_key), None)
    return templates.TemplateResponse("table_view.html", {"request": request, "table_name": table_name, "columns": table.columns, "results": results, "column_names": column_names, "primary_key": primary_key, "total_results": total_results, "page": page, "per_page": per_page, "sort_column": sort_column, "sort_order": sort_order})

@app.post("/table/{table_name}/insert", response_class=HTMLResponse)
async def insert_record(request: Request, table_name: str, db: Session = Depends(get_db)):
    form_data = await request.form()
    data_dict = {}
    for key, value in form_data.items():
        data_dict[key] = value

    table = Table(table_name, metadata, autoload_with=engine)
    try:
        stmt = insert(table).values(data_dict)
        db.execute(stmt)
        db.commit()
    except SQLAlchemyError as e:
        raise HTTPException(status_code=500, detail=str(e))

    return templates.TemplateResponse("insert_success.html", {"request": request, "table_name": table_name})

def get_primary_key(table):
    for column in table.columns:
        if column.primary_key:
            return column.name
    return None

@app.post("/table/{table_name}/update", response_class=HTMLResponse)
async def update_record(request: Request, table_name: str, db: Session = Depends(get_db)):
    form_data = await request.form()
    data_dict = {}

    table = Table(table_name, metadata, autoload_with=engine)
    primary_key = get_primary_key(table)
    primary_key_value = form_data.get(primary_key)

    for key, value in form_data.items():
        if key != primary_key:
            data_dict[key] = value

    try:
        stmt = update(table).where(getattr(table.c, primary_key) == primary_key_value).values(data_dict)
        db.execute(stmt)
        db.commit()
    except SQLAlchemyError as e:
        raise HTTPException(status_code=500, detail=str(e))

    return templates.TemplateResponse("update_success.html", {"request": request, "table_name": table_name})

@app.post("/table/{table_name}/delete", response_class=HTMLResponse)
async def delete_record(request: Request, table_name: str, db: Session = Depends(get_db)):
    form_data = await request.form()
    table = Table(table_name, metadata, autoload_with=engine)
    primary_key = get_primary_key(table)
    primary_key_value = form_data.get(primary_key)

    try:
        stmt = delete(table).where(getattr(table.c, primary_key) == primary_key_value)
        db.execute(stmt)
        db.commit()
    except SQLAlchemyError as e:
        raise HTTPException(status_code=500, detail=str(e))

    return templates.TemplateResponse("delete_success.html", {"request": request, "table_name": table_name})

@app.get("/table/{table_name}/search", response_class=HTMLResponse)
def search_records(request: Request, table_name: str, query: str, db: Session = Depends(get_db)):
    table = Table(table_name, metadata, autoload_with=engine)
    stmt = select(table)
    conditions = []
    for column in table.columns:
        if isinstance(column.type, (sqlalchemy.sql.sqltypes.String, sqlalchemy.sql.sqltypes.TEXT, sqlalchemy.sql.sqltypes.NVARCHAR)):
            column_conditions = or_(column.contains(query), column.ilike(f"%{query}%"))
            conditions.append(column_conditions)
    if conditions:
        stmt = stmt.where(and_(*conditions))
    results = db.execute(stmt).fetchall()
    column_names = [column.name for column in table.columns]
    compiled_stmt = stmt.compile(compile_kwargs={"literal_binds": True})
    logging.info(f"Executed SQL: {compiled_stmt}")
    return templates.TemplateResponse("search_results.html", {"request": request, "table_name": table_name, "results": results, "column_names": column_names})
