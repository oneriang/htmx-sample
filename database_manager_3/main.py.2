from fastapi import FastAPI, HTTPException, Request, Depends
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from sqlalchemy import create_engine, MetaData, Table, select, insert, update, delete, or_, and_, inspect, func, asc, desc
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.types import String, Text
import sqlalchemy
from typing import List, Dict
import logging

app = FastAPI()

app.mount(path="/static", app=StaticFiles(directory="static"), name="static")

templates = Jinja2Templates(directory="templates")

logging.basicConfig(level=logging.INFO)
logging.getLogger("sqlalchemy.engine").setLevel(logging.DEBUG)

# Database configuration
DATABASE_URL = "sqlite:///./my_database.db"
# engine = create_engine(DATABASE_URL)
engine = create_engine(DATABASE_URL, echo=True)
metadata = MetaData()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Get all table names
metadata.reflect(bind=engine)
table_names = metadata.tables.keys()

# Dependency to get a database session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Home page with a list of all tables
@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request, "table_names": table_names})

# View for a specific table
# @app.get("/table/{table_name}", response_class=HTMLResponse)
# def table_view(request: Request, table_name: str, db: Session = Depends(get_db)):
#     table = Table(table_name, metadata, autoload_with=engine)
#     results = db.execute(select(table)).fetchall()
#     column_names = [column.name for column in table.columns]
#     primary_key = next((column.name for column in table.columns if column.primary_key), None)
#     return templates.TemplateResponse("table_view.html", {"request": request, "table_name": table_name, "results": results, "column_names": column_names, "primary_key": primary_key})
# from typing import Optional

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

from typing import Optional

@app.get("/table/{table_name}", response_class=HTMLResponse)
def table_view(request: Request, table_name: str, page: int = 1, per_page: int = 10, sort_column: Optional[str] = None, sort_order: Optional[str] = None, db: Session = Depends(get_db)):
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


# Insert a new record
# @app.post("/table/{table_name}/insert")
# def insert_record(table_name: str, data: Dict, db: Session = Depends(get_db)):
#     table = Table(table_name, metadata, autoload_with=engine)
#     try:
#         db.execute(insert(table).values(data))
#         db.commit()
#     except SQLAlchemyError as e:
#         raise HTTPException(status_code=500, detail=str(e))
#     return RedirectResponse(f"/table/{table_name}")

from fastapi import Form

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

from sqlalchemy.exc import SQLAlchemyError

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

# # Update a record
# @app.post("/table/{table_name}/update")
# async def update_record(request: Request, table_name: str, db: Session = Depends(get_db)):
#     form_data = await request.form()
#     data_dict = {}
#     for key, value in form_data.items():
#         data_dict[key] = value

#     table = Table(table_name, metadata, autoload_with=engine)
#     primary_key_value = data.pop("primary_key_value")
#     primary_key_column = next((column for column in table.columns if column.primary_key), None)
#     if not primary_key_column:
#         raise HTTPException(status_code=400, detail="Table has no primary key")
#     try:
#         db.execute(update(table).where(primary_key_column == primary_key_value).values(data))
#         db.commit()
#     except SQLAlchemyError as e:
#         raise HTTPException(status_code=500, detail=str(e))
#     return RedirectResponse(f"/table/{table_name}")

# # Delete a record
# @app.post("/table/{table_name}/delete")
# def delete_record(table_name: str, primary_key_value: int, db: Session = Depends(get_db)):
#     table = Table(table_name, metadata, autoload_with=engine)
#     primary_key_column = next((column for column in table.columns if column.primary_key), None)
#     if not primary_key_column:
#         raise HTTPException(status_code=400, detail="Table has no primary key")
#     try:
#         db.execute(delete(table).where(primary_key_column == primary_key_value))
#         db.commit()
#     except SQLAlchemyError as e:
#         raise HTTPException(status_code=500, detail=str(e))
#     return RedirectResponse(f"/table/{table_name}")
from sqlalchemy.exc import SQLAlchemyError

@app.post("/table/{table_name}/delete", response_class=HTMLResponse)
async def delete_record(request: Request, table_name: str, db: Session = Depends(get_db)):
    form_data = await request.form()
    # primary_key_value = form_data.get("primary_key_value")

    # table = Table(table_name, metadata, autoload_with=engine)
    # primary_key = get_primary_key(table)

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

# # # # # # # # Search records
# # # # # # # @app.get("/table/{table_name}/search", response_class=HTMLResponse)
# # # # # # # def search_records(request: Request, table_name: str, query: str, db: Session = Depends(get_db)):
# # # # # # #     table = Table(table_name, metadata, autoload_with=engine)
# # # # # # #     stmt = select(table)
# # # # # # #     for column in table.columns:
# # # # # # #         if column.type in (String, text_type):
# # # # # # #             stmt = stmt.where(or_(column.contains(query), column.ilike(f"%{query}%")))
# # # # # # #     results = db.execute(stmt).fetchall()
# # # # # # #     column_names = [column.name for column in table.columns]
# # # # # # #     return templates.TemplateResponse("search_results.html", {"request": request, "table_name": table_name, "results": results, "column_names": column_names})

# # # # # # # Search records
# # # # # # @app.get("/table/{table_name}/search", response_class=HTMLResponse)
# # # # # # def search_records(request: Request, table_name: str, query: str, db: Session = Depends(get_db)):
# # # # # #     table = Table(table_name, metadata, autoload_with=engine)
# # # # # #     stmt = select(table)
# # # # # #     for column in table.columns:
# # # # # #         if column.type in (String, Text):
# # # # # #             stmt = stmt.where(or_(column.contains(query), column.ilike(f"%{query}%")))
# # # # # #     results = db.execute(stmt).fetchall()
# # # # # #     print(results)
# # # # # #     column_names = [column.name for column in table.columns]
# # # # # #     return templates.TemplateResponse("search_results.html", {"request": request, "table_name": table_name, "results": results, "column_names": column_names})

# # # # # @app.get("/table/{table_name}/search", response_class=HTMLResponse)
# # # # # def search_records(request: Request, table_name: str, query: str, db: Session = Depends(get_db)):
# # # # #     table = Table(table_name, metadata, autoload_with=engine)
# # # # #     stmt = select(table)
# # # # #     conditions = []
# # # # #     for column in table.columns:
# # # # #         if column.type in (String, Text):
# # # # #             conditions.append(column.contains(query))
# # # # #             conditions.append(column.ilike(f"%{query}%"))
# # # # #     if conditions:
# # # # #         stmt = stmt.where(or_(*conditions))
# # # # #     results = db.execute(stmt).fetchall()
# # # # #     print(results)
# # # # #     column_names = [column.name for column in table.columns]
# # # # #     return templates.TemplateResponse("search_results.html", {"request": request, "table_name": table_name, "results": results, "column_names": column_names})
# # # # @app.get("/table/{table_name}/search", response_class=HTMLResponse)
# # # # def search_records(request: Request, table_name: str, query: str, db: Session = Depends(get_db)):
# # # #     table = Table(table_name, metadata, autoload_with=engine)
# # # #     stmt = select(table)
# # # #     conditions = []
# # # #     for column in table.columns:
# # # #         if column.type in (String, Text):
# # # #             column_conditions = or_(column.contains(query), column.ilike(f"%{query}%"))
# # # #             conditions.append(column_conditions)
# # # #     if conditions:
# # # #         stmt = stmt.where(and_(*conditions))

# # # #     # 打印 SQL 语句
# # # #     compiled_stmt = stmt.compile(compile_kwargs={"literal_binds": True})
# # # #     print('打印 SQL 语句')
# # # #     print(compiled_stmt)

# # # #     results = db.execute(stmt).fetchall()
# # # #     column_names = [column.name for column in table.columns]

# # # #     # # Log the executed SQL statement
# # # #     # logging.info(f"Executed SQL: {stmt.compile(dialect=engine.dialect)}")

# # # #     return templates.TemplateResponse("search_results.html", {"request": request, "table_name": table_name, "results": results, "column_names": column_names})


# # # @app.get("/table/{table_name}/search", response_class=HTMLResponse)
# # # def search_records(request: Request, table_name: str, query: str, db: Session = Depends(get_db)):
# # #     table = Table(table_name, metadata, autoload_with=engine)
# # #     stmt = select(table)
# # #     conditions = []
# # #     for column in table.columns:
# # #         print('1')
# # #         print(column.type)
# # #         if column.type in (String, Text):
# # #             print('2')
# # #             column_conditions = or_(column.contains(query), column.ilike(f"%{query}%"))
# # #             conditions.append(column_conditions)
# # #     if conditions:
# # #         print('aaa')
# # #         stmt = stmt.where(and_(*conditions))

# # #     # 打印 SQL 语句
# # #     compiled_stmt = stmt.compile(compile_kwargs={"literal_binds": True})
# # #     print('打印 SQL 语句')
# # #     print(compiled_stmt)

# # #     results = db.execute(stmt).fetchall()
# # #     column_names = [column.name for column in table.columns]

# # #     # Log the executed SQL statement
# # #     logging.info(f"Executed SQL: {stmt.compile(dialect=engine.dialect)}")

# # #     return templates.TemplateResponse("search_results.html", {"request": request, "table_name": table_name, "results": results, "column_names": column_names})

# # @app.get("/table/{table_name}/search", response_class=HTMLResponse)
# # def search_records(request: Request, table_name: str, query: str, db: Session = Depends(get_db)):
# #     table = Table(table_name, metadata, autoload_with=engine)
# #     stmt = select(table)
# #     conditions = []
# #     for column in table.columns:
# #         column_type = inspect(column.type).python_type
# #         if column_type in (str,):
# #             column_conditions = or_(column.contains(query), column.ilike(f"%{query}%"))
# #             conditions.append(column_conditions)
# #     if conditions:
# #         stmt = stmt.where(and_(*conditions))
# #     results = db.execute(stmt).fetchall()
# #     column_names = [column.name for column in table.columns]

# #     # Log the executed SQL statement with bound parameters
# #     compiled_stmt = stmt.compile(compile_kwargs={"literal_binds": True})
# #     logging.info(f"Executed SQL: {compiled_stmt}")

# #     return templates.TemplateResponse("search_results.html", {"request": request, "table_name": table_name, "results": results, "column_names": column_names})
# @app.get("/table/{table_name}/search", response_class=HTMLResponse)
# def search_records(request: Request, table_name: str, query: str, db: Session = Depends(get_db)):
#     table = Table(table_name, metadata, autoload_with=engine)
#     stmt = select(table)
#     conditions = []
#     for column in table.columns:
#         print(column.type)
#         if column.type in (sqlalchemy.sql.sqltypes.String, sqlalchemy.sql.sqltypes.TEXT):
#             column_conditions = or_(column.contains(query), column.ilike(f"%{query}%"))
#             conditions.append(column_conditions)
#     if conditions:
#         stmt = stmt.where(and_(*conditions))
#     results = db.execute(stmt).fetchall()
#     column_names = [column.name for column in table.columns]

#     # Log the executed SQL statement with bound parameters
#     compiled_stmt = stmt.compile(compile_kwargs={"literal_binds": True})
#     logging.info(f"Executed SQL: {compiled_stmt}")

#     return templates.TemplateResponse("search_results.html", {"request": request, "table_name": table_name, "results": results, "column_names": column_names})
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

    # Log the executed SQL statement with bound parameters
    compiled_stmt = stmt.compile(compile_kwargs={"literal_binds": True})
    logging.info(f"Executed SQL: {compiled_stmt}")

    return templates.TemplateResponse("search_results.html", {"request": request, "table_name": table_name, "results": results, "column_names": column_names})
