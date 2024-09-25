import os
import uvicorn
from datetime import datetime
from fastapi import FastAPI, Request, Form, HTTPException
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from sqlalchemy import create_engine, MetaData, Table, select, insert, update, delete, inspect, or_, and_, func, desc, asc
from sqlalchemy.orm import sessionmaker, class_mapper
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.sql import expression
from sqlalchemy.sql.sqltypes import String, Integer, DateTime, Date, Boolean, Enum
from sqlalchemy import inspect, String, Integer, Float, DateTime, Date, Boolean, Enum

from pydantic import BaseModel, Field
from typing import Dict, Any, List, Union, Optional
from jinja2 import Template

import yaml

import logging

import transaction_module
from transaction_module import convert_value

import gv as gv

app = FastAPI()

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")
            
# 添加 min 函数到模板上下文
templates.env.globals['min'] = min

# Database connection configuration
DATABASE_URL = "sqlite:///./Chinook.db"
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
metadata = MetaData()

# Reflect existing database tables
metadata.reflect(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def load_data_from_html(filename: str) -> Optional[str]:
    try:
        with open(filename, "r", encoding="utf-8") as file:
            return file.read()
    except IOError as e:
        logging.error(f"Error loading data from {filename}: {e}")
        return None

def load_data_from_yaml(filename: str) -> Optional[Dict[str, Any]]:
    try:
        with open(filename, "r", encoding="utf-8") as file:
            return yaml.safe_load(file)
    except (IOError, yaml.YAMLError) as e:
        logging.error(f"Error loading YAML data from {filename}: {e}")
        return None
        
gv.BASE_HTML = None
gv.HTML_TEMPLATES = None
gv.YAML_CONFIG = None

def load_data():
    
  gv.BASE_HTML = load_data_from_html('base_html.html')
  
  gv.HTML_TEMPLATES = load_data_from_yaml('html_templates.yaml')
  
  gv.YAML_CONFIG = load_data_from_yaml('yaml_config.yaml')

load_data()

def get_configs():
    return get_table_config()
    
def getTables():
    tables = get_table_names()
    values = []
    for t in tables:
        values.append(
            {
                'link': '/table/' + t,
                'text': t
            }
        )
    return values

def getTables1():
    tables = get_table_names()
    values = []
    for t in tables:
        values.append(
            {
                'component_id': 'main_data_table',
                'text': t
            }
        )
    return values

# 修改渲染函数
def generate_html(component: Dict[str, Any]) -> str:
    for key in ['config', 'data', 'value']:
        if key in component and isinstance(component[key], str):
            if component[key] in globals():
                component[key] = globals()[component[key]]()

    template = Template(gv.HTML_TEMPLATES.get(component['type'], ''))
    
    rendered_children = {'_unnamed': []}
    if 'children' in component:
      if isinstance(component['children'], list):
        print("这是一个数组（列表）")
        rendered_children = [generate_html(resolve_component(child)) for child in component.get('children', [])]
      else:
        print("这不是一个数组（列表）")
        for key, value in component['children'].items():
            if isinstance(key, str):  # Named children
                rendered_children[key] = [generate_html(resolve_component(child)) for child in value]
            elif isinstance(key, int):  # Unnamed children
                rendered_children['_unnamed'].append(generate_html(resolve_component(value)))

    return template.render(
        attributes=component.get('attributes', {}),
        configs=component.get('config', {}),
        data=component.get('data', {}),
        value=component.get('value', []),
        children=rendered_children,
        min=min
    )

# 辅助函数：解析组件引用
def resolve_component(comp):
    if isinstance(comp, dict) and '$ref' in comp:
        return gv.component_dict[comp['$ref']]
    return comp

# 修改加载配置函数
def load_page_config() -> Dict[str, Any]:
    # config = yaml.safe_load(YAML_CONFIG)
    config = gv.YAML_CONFIG
    
    gv.component_dict = {
        comp['id']: comp 
        for comp in config.get('component_definitions', {}).values()
    }
    
    def resolve_components(components):
        resolved = []
        for comp in components:
            if isinstance(comp, dict) and '$ref' in comp:
                resolved.append(resolve_component(comp))
            elif isinstance(comp, dict) and 'children' in comp:
                resolved_comp = comp.copy()
                resolved_comp['children'] = resolve_components(comp['children'])
                resolved.append(resolved_comp)
            else:
                resolved.append(comp)
        return resolved

    config['components'] = resolve_components(config['components'])
    
    return config

# 主渲染函数保持不变
@app.get("/page", response_class=HTMLResponse)
async def render_page(request: Request):
    gv.request = request
    
    load_data()

    page_config = load_page_config()
    rendered_components = [generate_html(component) for component in page_config['components']]

    template = Template(gv.BASE_HTML)
    return template.render(
        page_title=page_config['title'],
        components=rendered_components,
        min=min
    )

@app.get("/component", response_class=HTMLResponse)
async def rendered_component(request: Request):
    gv.request = request
    query_params = dict(request.query_params)

    if 'component_id' not in query_params:
        return ''
    
    component_id = query_params['component_id']
    
    load_page_config()
    
    return generate_html(gv.component_dict[component_id])


@app.get("/")
async def read_root(request: Request):
    tables = get_table_names()
    return templates.TemplateResponse("all_in_one.html", {"request": request, "tables": tables})

@app.get("/table/{table_name}")
async def read_table(request: Request, table_name: str):
    if table_name not in metadata.tables:
        raise HTTPException(status_code=404, detail="Table not found")
    
    table_config = get_table_config(table_name)
    return templates.TemplateResponse("all_in_one.html", {
        "request": request,
        "table_name": table_name,
        "table_config": table_config
    })

def generate_table_config(engine, table_name):
    inspector = inspect(engine)
    columns = inspector.get_columns(table_name)
    
    config_path = f'table_configs/{table_name}_config.yaml'
    
    # Check if configuration file exists
    if os.path.exists(config_path):
        # Read existing configuration file
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
            return config
        
    config = {
        "table_name": table_name,
        "columns": []
    }

    for column in columns:
        column_config = {
            "name": column['name'],
            "label": column['name'],
            "type": str(column['type']),
            "nullable": column['nullable'],
            "primary_key": column['primary_key']
        }

        # Determine input type and additional properties
        if isinstance(column['type'], String):
            column_config['input_type'] = 'text'
        elif isinstance(column['type'], (Integer, Float)):
            column_config['input_type'] = 'number'
        elif isinstance(column['type'], (DateTime, Date)):
            column_config['input_type'] = 'date'
        elif isinstance(column['type'], Boolean):
            column_config['input_type'] = 'checkbox'
        elif isinstance(column['type'], Enum):
            column_config['input_type'] = 'select'
            column_config['options'] = column['type'].enums
        else:
            column_config['input_type'] = 'text'

        config['columns'].append(column_config)

    # Save configuration to a YAML file
    with open(f'table_configs/{table_name}_config.yaml', 'w') as f:
        yaml.dump(config, f, default_flow_style=False)

    return config

# Generate configurations for all tables
def generate_all_table_configs(engine):
    inspector = inspect(engine)
    for table_name in inspector.get_table_names():
        generate_table_config(engine, table_name)

# Generate table configurations
generate_all_table_configs(engine)

def get_table_config(table_name=None):

    request = gv.request
    
    search_params = {}
    if request:
      # Get all query parameters
      search_params = dict(request.query_params)
      if 'table_name' in search_params:
        table_name = search_params['table_name']
        
    if table_name is None:
      table_name = 'Genre'
      
    with open(f'table_configs/{table_name}_config.yaml', 'r') as f:
        configs = yaml.safe_load(f)
        configs['component_id'] = 'main_data_table'
        return configs

def get_primary_key(table):
    return next(iter(table.primary_key.columns)).name

def get_table_names():
    inspector = inspect(engine)
    return inspector.get_table_names()

def apply_search_filter(query, table, column_config, value):
    if value:
        column = getattr(table.c, column_config['name'])
        input_type = column_config.get('input_type', 'text')
        
        if input_type == 'text':
            return query.where(column.ilike(f"%{value}%"))
        elif input_type == 'number':
            try:
                value = float(value)
                return query.where(column == value)
            except ValueError:
                return query
        elif input_type in ('date', 'datetime'):
            try:
                value = datetime.strptime(value, "%Y-%m-%d")
                return query.where(column == value)
            except ValueError:
                return query
        elif input_type == 'checkbox':
            value = value.lower() in ('true', '1', 'yes', 'on')
            return query.where(column == value)
        elif input_type == 'select':
            return query.where(column == value)
    return query

def get_table_data_params(
        request: Request = None, 
        table_name: str = None, 
        page: int = 1, 
        page_size: int = 2,
        sort_column: str | None = None,
        sort_direction: str = 'asc'
    ):
    if request is None:
        request = gv.request
    
    search_params = {}
    if request:
      # Get all query parameters
      search_params = dict(request.query_params)
      # Remove known parameters

      if 'page' in search_params:
        page = int(search_params['page'])

      if 'page_size' in search_params:
        page_size = int(search_params['page_size'])
      
      if 'sort_column' in search_params:
        sort_column = search_params['sort_column']

      if 'sort_direction' in search_params:
        sort_direction = search_params['sort_direction']

      if 'table_name' in search_params:
        table_name = search_params['table_name']

      for param in ['page', 'page_size', 'sort_column', 'sort_direction']:
          search_params.pop(param, None)

    if table_name is None:
      table_name = 'Genre'

    if table_name not in metadata.tables:
        raise HTTPException(status_code=404, detail="Table not found")
    
    table_config = get_table_config(table_name)
    table = metadata.tables[table_name]
    primary_key = next(col['name'] for col in table_config['columns'] if col.get('primary_key', False))
    offset = (page - 1) * page_size
    
    query = select(table.columns)
    
    # Apply search filters for each column based on JSON configuration
    for column_config in table_config['columns']:
        if column_config['name'] in search_params:
            query = apply_search_filter(query, table, column_config, search_params[column_config['name']])
    
    # Apply sorting if a sort column is specified
    if sort_column and sort_column in table.columns:
        sort_func = desc if sort_direction.lower() == 'desc' else asc
        query = query.order_by(sort_func(getattr(table.c, sort_column)))
    
    with SessionLocal() as session:
        count_query = select(func.count()).select_from(query.alias())
        total_items = session.execute(count_query).scalar()
        result = session.execute(query.offset(offset).limit(page_size)).fetchall()
        
    total_pages = (total_items + page_size - 1) // page_size
    
    return {
        "request": request,
        "table_name": table_name,
        "columns": [col['name'] for col in table_config['columns']],
        "rows": result,
        "primary_key": primary_key,
        "page": page,
        "page_size": page_size,
        "total_items": total_items,
        "total_pages": total_pages,
        "table_config": table_config,
        "sort_column": sort_column,
        "sort_direction": sort_direction,
        "search_params": search_params
    }

@app.get("/table_content/{table_name}")
async def read_table_content(
        request: Request, 
        table_name: str, 
        page: int = 1, 
        page_size: int = 10,
        sort_column: str | None = None,
        sort_direction: str = 'asc'
    ):
    if table_name not in metadata.tables:
        raise HTTPException(status_code=404, detail="Table not found")
    
    table_config = get_table_config(table_name)
    table = metadata.tables[table_name]
    primary_key = next(col['name'] for col in table_config['columns'] if col.get('primary_key', False))
    offset = (page - 1) * page_size
    
    query = select(table.columns)
    
    # Get all query parameters
    search_params = dict(request.query_params)
    # Remove known parameters
    for param in ['page', 'page_size', 'sort_column', 'sort_direction']:
        search_params.pop(param, None)
    
    # Apply search filters for each column based on JSON configuration
    for column_config in table_config['columns']:
        if column_config['name'] in search_params:
            query = apply_search_filter(query, table, column_config, search_params[column_config['name']])
    
    # Apply sorting if a sort column is specified
    if sort_column and sort_column in table.columns:
        sort_func = desc if sort_direction.lower() == 'desc' else asc
        query = query.order_by(sort_func(getattr(table.c, sort_column)))
    
    with SessionLocal() as session:
        count_query = select(func.count()).select_from(query.alias())
        total_items = session.execute(count_query).scalar()
        result = session.execute(query.offset(offset).limit(page_size)).fetchall()
        
    total_pages = (total_items + page_size - 1) // page_size
    
    return templates.TemplateResponse("table_content.html", {
        "request": request,
        "table_name": table_name,
        "columns": [col['name'] for col in table_config['columns']],
        "rows": result,
        "primary_key": primary_key,
        "page": page,
        "page_size": page_size,
        "total_items": total_items,
        "total_pages": total_pages,
        "table_config": table_config,
        "sort_column": sort_column,
        "sort_direction": sort_direction,
        "search_params": search_params
    })

@app.get("/create1/{table_name}", response_class=HTMLResponse)
async def create_form1(request: Request, table_name: str):
    if table_name not in metadata.tables:
        raise HTTPException(status_code=404, detail="Table not found")
    
    table = metadata.tables[table_name]
    columns = [col.name for col in table.columns if col.name != get_primary_key(table)]
    return templates.TemplateResponse("create_form.html", {
        "request": request, 
        "table_name": table_name, 
        "columns": columns,
    })
    
@app.get("/create", response_class=HTMLResponse)
async def create_form(request: Request):
    gv.request = request

    table_name = None
    id = None
      
    query_params = dict(request.query_params)

    if 'table_name' in query_params:
      table_name = query_params['table_name']

    if 'id' in query_params:
      id = query_params['id']

    if table_name is None:
      table_name = 'Genre'
    
    if id is None:
      id = 22

    table_config = get_table_config(table_name)
    
    primary_key = None
    
    #table = metadata.tables[table_name]

    #primary_key = get_primary_key(table)
    
    ''' 
    with SessionLocal() as session:
        stmt = select(table).where(getattr(table.c, primary_key) == id)
        result = session.execute(stmt).fetchone()._asdict()
    '''
    
    if True:
      
        #data = dict(result)
        
        component_id = None
    
        if 'component_id' in query_params:
          component_id = query_params['component_id']
        
        if component_id is None:
          component_id = 'form_create'
          
        load_page_config()

        gv.component_dict[component_id]['config'] = {
            'table_name':table_name,
            'id':id,
            'data': {},
            'primary_key':primary_key,
            'table_config':table_config
        }
        
        return generate_html(gv.component_dict[component_id])
        
    raise HTTPException(status_code=404, detail="Item not found")

@app.post("/create/{table_name}")
async def create_item(table_name: str, request: Request):
    if table_name not in metadata.tables:
        raise HTTPException(status_code=404, detail="Table not found")
    
    table = metadata.tables[table_name]
    form_data = await request.form()
    data = {key: value for key, value in form_data.items() if key in table.columns.keys()}
    
    try:
        with SessionLocal() as session:
            stmt = insert(table).values(**data)
            session.execute(stmt)
            session.commit()
        return templates.TemplateResponse("table_content.html", {
            "request": request,
            "table_name": table_name,
            "columns": table.columns.keys(),
            "rows": session.execute(select(table)).fetchall(),
            "primary_key": get_primary_key(table),
            "page": 1,
            "page_size": 10,
            "total_items": session.execute(select(func.count()).select_from(table)).scalar(),
            "total_pages": 1,
            "search": "",
        })
    except SQLAlchemyError as e:
        return {"success": False, "message": str(e)}

@app.get("/edit", response_class=HTMLResponse)
async def edit_form(request: Request):
    gv.request = request

    table_name = None
    id = None
      
    query_params = dict(request.query_params)

    if 'table_name' in query_params:
      table_name = query_params['table_name']

    if 'id' in query_params:
      id = query_params['id']

    if table_name is None:
      table_name = 'Genre'
    
    if id is None:
      id = 22

    table_config = get_table_config(table_name)
    
    table = metadata.tables[table_name]

    primary_key = get_primary_key(table)
     
    with SessionLocal() as session:
        stmt = select(table).where(getattr(table.c, primary_key) == id)
        result = session.execute(stmt).fetchone()._asdict()
    
    if result:
      
        data = dict(result)
        
        component_id = None
    
        if 'component_id' in query_params:
          component_id = query_params['component_id']
        
        if component_id is None:
          component_id = 'form_edit'
          
        load_page_config()

        gv.component_dict[component_id]['config'] = {
            'table_name':table_name,
            'id':id,
            'data':data,
            'primary_key':primary_key,
            'table_config':table_config
        }
        
        return generate_html(gv.component_dict[component_id])
        '''        
        rendered_components = [generate_html(gv.component_dict[component_id])]

        template = Template(BASE_HTML)
        return template.render(
            components=rendered_components,
            min=min
        )
        '''
        
    raise HTTPException(status_code=404, detail="Item not found")

@app.post("/edit/{table_name}/{id}")
async def edit_item(table_name: str, id: str, request: Request):
    print('edit_item')
    if table_name not in metadata.tables:
        raise HTTPException(status_code=404, detail="Table not found")
    
    table = metadata.tables[table_name]
    primary_key = get_primary_key(table)
    form_data = await request.form()
    data = {key: value for key, value in form_data.items() if key in table.columns.keys()}
    
    for key in data:
        data[key] = convert_value(table.c[key].type, data[key])
    
    try:
        with SessionLocal() as session:
            stmt = update(table).where(getattr(table.c, primary_key) == id).values(**data)
            session.execute(stmt)
            session.commit()
            return ''
            
    except SQLAlchemyError as e:
        print(e)
        return {"success": False, "message": str(e)}

@app.delete("/delete/{table_name}/{id}")
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
        # return {"success": True, "message": "Item deleted successfully"}
        return "Item deleted successfully"
    except SQLAlchemyError as e:
        return {"success": False, "message": str(e)}

def get_column_type(column_type):
    if isinstance(column_type, String):
        return "text"
    elif isinstance(column_type, Integer):
        return "number"
    elif isinstance(column_type, Boolean):
        return "checkbox"
    elif isinstance(column_type, (DateTime, Date)):
        return "date"
    else:
        return "text"  # 默认为文本输入

def generate_form_config(table_name):
    table = metadata.tables[table_name]
    inspector = inspect(engine)
    pk_constraint = inspector.get_pk_constraint(table_name)
    primary_keys = pk_constraint['constrained_columns'] if pk_constraint else []

    fields = []
    for column in table.columns:
        field = {
            "name": column.name,
            "label": column.name.replace('_', ' ').title(),
            "type": get_column_type(column.type),
            "required": not column.nullable and column.name not in primary_keys,
            "readonly": column.name in primary_keys
        }
        fields.append(field)

    return {"fields": fields}

@app.get("/form_config/{table_name}")
async def get_form_config(table_name: str):
    if table_name not in metadata.tables:
        raise HTTPException(status_code=404, detail="Table not found")
    return generate_form_config(table_name)

@app.get("/record/{table_name}/{id}")
async def get_record(table_name: str, id: str):
    if table_name not in metadata.tables:
        raise HTTPException(status_code=404, detail="Table not found")
    
    table = metadata.tables[table_name]
    primary_key = get_primary_key(table)
    
    with SessionLocal() as session:
        stmt = select(table).where(getattr(table.c, primary_key) == id)
        result = session.execute(stmt).fetchone()
        if result:
            return dict(result._mapping)
        else:
            raise HTTPException(status_code=404, detail="Record not found")

@app.get("/execute_all_transactions")
def execute_all_transactions():
    try:
        transaction_module.execute_all_transactions(SessionLocal())
    except Exception as e:
        logger.error(f"Unexpected error executing transactions: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

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
