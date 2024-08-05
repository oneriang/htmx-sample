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

from transaction_module import convert_value

import gv as gv

app = FastAPI()

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

# HTML templates as Python strings
BASE_HTML = """
  <!DOCTYPE html>
  <html lang="en" data-theme="light">
      <head>
          <meta charset="UTF-8">
          <meta name="viewport" content="width=device-width, initial-scale=1.0">
          <title>{{ page_title }}</title>
          <script src="https://unpkg.com/htmx.org@1.9.2"></script>
         
          
        <link href="https://cdn.jsdelivr.net/npm/daisyui@4.12.10/dist/full.min.css" rel="stylesheet" type="text/css" />
        <script src="https://cdn.tailwindcss.com"></script>
      </head>
  <body>
    {% for component in components %}
        {{ component | safe }}
    {% endfor %}
    <style>
        .modal1 {
            display: none;
            position: fixed;
            z-index: 1;
            left: 0;
            top: 0;
            width: 100%;
            height: 100%;
            overflow: auto;
            background-color: rgba(0, 0, 0, 0.4);
        }

        .modal-content1 {
            background-color: #fefefe;
            margin: 15% auto;
            padding: 20px;
            border: 1px solid #888;
            width: 80%;
            max-width: 500px;
        }
    </style>

    <script>
        function showModal() {
            document.getElementById('modal_form').showModal();
        }

        function hideModal() {
            document.getElementById('modal_form').close();
        }

        document.body.addEventListener('htmx:afterSwap', function (event) {
            if (event.detail.target.id === 'table-content') {
                hideModal();
            }
        });
    </script>
  </body>
  </html>
"""

HTML_TEMPLATES = {
    'container': '''
        <div class="container mx-auto {{ attributes.class.value }}">
            {% for child in children %}
                {{ child | safe }}
            {% endfor %}
        </div>
    ''',
    'card': '''
        <div class="card w-full {{ attributes.class.value }}">
            <div class="card-body">
                <h2 class="card-title">{{ attributes.title.value }}</h2>
                <p>{{ attributes.content.value }}</p>
                {% for child in children %}
                    {{ child | safe }}
                {% endfor %}
            </div>
        </div>
    ''',
    'grid': '''
        <div class="grid grid-cols-{{ attributes.columns.value }} {{ attributes.class.value }}">
            {% for child in children %}
                <div class="col-span-1">{{ child | safe }}</div>
            {% endfor %}
        </div>
    ''',
    'list': '''
        <ul class="menu bg-base-200 w-56 rounded-box">
            {% for item in value %}
                {% if item.get %}
                    <li>
                        <a href="#"
                            hx-get="{{- '/component?' -}}
                            {{- 'table_name=' ~ item.text -}}&
                            {{- 'component_id=' ~ item.component_id -}}"
                            hx-target="#table-content"
                            >
                                {{ item.text }}
                            </a>
                {% else %}
                    <li><a class="link" href="{{item.link}}">{{ item.text }}</a></li>
                {% endif %}
            {% endfor %}
        </ul>
    ''',
    'data-table': '''
      <div class="overflow-x-auto mt-4" id="table-content">
      {{ configs.table_name }}
          <table class="min-w-full bg-white border-collapse">
              <thead>
                  <tr>
                      <th class="border px-4 py-2 sticky-left sticky-left-shadow">Actions</th>
                      {% for column in configs.columns %}
                      {% if not column['is_hidden'] %}
                      <th class="border px-4 py-2">
                          <div style="overflow: hidden; resize: horizontal;">
                            <a href="#"
                            hx-get="{{- '/component?' -}}
                            {{- 'component_id=' ~ configs.component_id -}}&
                            {{- 'page=' ~ page -}}&
                            {{- 'search=' ~ search -}}&
                            {{- 'sort_column=' ~ column['name'] -}}&
                            {{- 'sort_direction=' -}}
                            {%- if sort_column == column['name'] and sort_direction == 'asc' -%}
                                {{- 'desc' -}}
                            {%- else -%}
                                {{- 'asc' -}}
                            {%- endif -%}"
                            hx-target="#table-content"
                            class="{% if sort_column == column['name'] %}sort-{{ sort_direction }}{% endif %}"
                            >
                                {{ column['label'] or column['name'] }}
                                <span class="sort-icon"></span>
                            </a>
                          </div>
                      </th>
                      {% endif %}
                      {% endfor %}
                  </tr>
              </thead>
              <tbody>
                  {% for row in data.rows %}
                  <tr class="hover:bg-gray-100">
                      <td class="border px-4 py-2 sticky-left sticky-left-shadow">
                          <button hx-get="/edit?table_name={{ configs.table_name }}&id={{ row[data.primary_key] }}" hx-target="#modal-content"
                              hx-trigger="click" onclick="modal_form.showModal()" class="text-blue-500 hover:underline">Edit</button>
                          <button hx-get="/edit?table_name={{ configs.table_name }}&id={{ row[data.primary_key] }}" hx-target="#modal-content"
                              hx-trigger="click" onclick="modal_form.showModal()" class="text-blue-500 hover:underline">Edit</button>
                          <button onclick="showDeleteModal('{{ configs.table_name }}', '{{ row[data.primary_key] }}')"
                              class="text-red-500 hover:underline">Delete</button>
                      </td>
                      {% for column in configs.columns %}
                      {% if not column['is_hidden'] %}
                      <td class="border px-4 py-2">{{ row[column['name']] or '' }}</td>
                      {% endif %}
                      {% endfor %}
                  </tr>
                  {% endfor %}
              </tbody>
          </table>
          <div class="mt-4 flex justify-between items-center">
            <p>Showing 
                {{ (data.page - 1) * data.page_size + 1 }} 
                to 
                {{ min(data.page * data.page_size, data.total_items) }} 
                of 
                {{ data.total_items }} 
                records
            </p>
            <div class="flex space-x-2">
                {% if data.page > 1 %}
                    <button
                        hx-get="{{- '/component?' -}}
                        {{- 'component_id=' ~ configs.component_id -}}&
                        {{- 'page=' ~ (data.page - 1) -}}&
                        {{- 'page_size=' ~ data.page_size -}}&
                        {{- 'sort_column=' ~ data.sort_column -}}&
                        {{- 'sort_direction=' ~ data.sort_direction -}}
                        {%- for key, value in data.search_params.items() -%}
                            &{{ key }}={{ value }}
                        {%- endfor -%}"
                        hx-target="#table-content"
                        class="bg-blue-500 text-white px-4 py-2 rounded"
                    >
                        Previous
                    </button>
                {% endif %}
                {% if data.page < data.total_pages %} 
                    <button
                        hx-get="{{- '/component?' -}}
                        {{- 'component_id=' ~ configs.component_id -}}&
                        {{- 'page=' ~ (data.page + 1) -}}&
                        {{- 'page_size=' ~ data.page_size -}}&
                        {{- 'sort_column=' ~ data.sort_column -}}&
                        {{- 'sort_direction=' ~ data.sort_direction -}}
                        {%- for key, value in data.search_params.items() -%}
                            &{{ key }}={{ value }}
                        {%- endfor -%}"
                        hx-target="#table-content"
                        class="bg-blue-500 text-white px-4 py-2 rounded"
                    >
                        Next
                    </button>
                {% endif %}
                    <button
                        hx-get="{{- '/component?' -}}
                        {{- 'component_id=' ~ configs.component_id -}}&
                        {{- 'page=' ~ data.page -}}&
                        {{- 'page_size=' ~ data.page_size -}}&
                        {{- 'sort_column=' ~ data.sort_column -}}&
                        {{- 'sort_direction=' ~ data.sort_direction -}}
                        {%- for key, value in data.search_params.items() -%}
                            &{{ key }}={{ value }}
                        {%- endfor -%}"
                        hx-target="#table-content"
                        id="btn-table-refresh"
                        class="bg-blue-500 text-white px-4 py-2 rounded"
                    >
                        Refresh
                    </button>
            </div>
          </div>
        </div>
    ''',
    'table': '''
        <div class="overflow-x-auto">
            <table class="table {{ attributes.class.value }}">
                <thead>
                    <tr>
                        {% for header in attributes.headers.value %}
                            <th>{{ header }}</th>
                        {% endfor %}
                    </tr>
                </thead>
                <tbody>
                    {% for row in attributes.rows.value %}
                        <tr>
                            {% for cell in row %}
                                <td>{{ cell }}</td>
                            {% endfor %}
                        </tr>
                    {% endfor %}
                </tbody>
            </table>
        </div>
    ''',
    'form': '''
        <form class="{{ attributes.class.value }}">
            {% for field in attributes.fields.value %}
                <div class="form-control w-full mb-4">
                    <label class="label">
                        <span class="label-text">{{ field.label }}</span>
                    </label>
                    {% if field.type == 'text' or field.type == 'email' or field.type == 'password' or field.type == 'number' or field.type == 'date' %}
                        <input {% if field.disabled %}disabled{% endif %} {% if field.readonly %}readonly{% endif %} type="{{ field.type }}" name="{{ field.name }}" placeholder="{{ field.placeholder }}" class="input input-bordered w-full" {% if field.required %}required{% endif %}>
                    {% elif field.type == 'textarea' %}
                        <textarea name="{{ field.name }}" placeholder="{{ field.placeholder }}" class="textarea textarea-bordered w-full" {% if field.required %}required{% endif %}></textarea>
                    {% elif field.type == 'select' %}
                        <select name="{{ field.name }}" class="select select-bordered w-full" {% if field.required %}required{% endif %}>
                            {% for option in field.options %}
                                <option value="{{ option.value }}">{{ option.label }}</option>
                            {% endfor %}
                        </select>
                    {% elif field.type == 'checkbox' %}
                        <div class="flex items-center mt-2">
                            <input type="checkbox" name="{{ field.name }}" class="checkbox" {% if field.required %}required{% endif %}>
                            <span class="ml-2">{{ field.checkboxLabel }}</span>
                        </div>
                    {% elif field.type == 'radio' %}
                        <div class="flex flex-col mt-2">
                            {% for option in field.options %}
                                <label class="flex items-center mb-2">
                                    <input type="radio" name="{{ field.name }}" value="{{ option.value }}" class="radio" {% if field.required %}required{% endif %}>
                                    <span class="ml-2">{{ option.label }}</span>
                                </label>
                            {% endfor %}
                        </div>
                    {% elif field.type == 'file' %}
                        <input type="file" name="{{ field.name }}" class="file-input file-input-bordered w-full" {% if field.required %}required{% endif %}>
                    {% endif %}
                    {% if field.helpText %}
                        <label class="label">
                            <span class="label-text-alt text-info">{{ field.helpText }}</span>
                        </label>
                    {% endif %}
                </div>
            {% endfor %}
            <button type="submit" class="btn btn-primary w-full mt-4">{{ attributes.submit_text.value }}</button>
        </form>
    ''',
    'navbar': '''
        <div class="navbar bg-base-100 {{ attributes.class.value }}">
            <div class="flex-1">
                <a class="btn btn-ghost normal-case text-xl">{{ attributes.title.value }}</a>
            </div>
            <div class="flex-none hidden md:block">
                <ul class="menu menu-horizontal px-1">
                    {% for item in attributes.menu_items.value %}
                        <li><a href="{{ item.link }}">{{ item.text }}</a></li>
                    {% endfor %}
                </ul>
            </div>
            <div class="flex-none md:hidden">
                <button class="btn btn-square btn-ghost" data-drawer-target="my-drawer">
                    <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" class="inline-block w-5 h-5 stroke-current"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 12h16M4 18h16"></path></svg>
                </button>
            </div>
        </div>
    ''',
    'button': '''
        <button class="btn {{ attributes.class.value if attributes.class and attributes.class.value else '' }}" 
                {% if attributes.modal_target and attributes.modal_target.value %}data-modal-target="{{ attributes.modal_target.value }}"{% endif %}
                {% if attributes.drawer_target and attributes.drawer_target.value %}data-drawer-target="{{ attributes.drawer_target.value }}"{% endif %}
                {% if attributes.onclick and attributes.onclick.value %}onclick="{{ attributes.onclick.value }}"{% endif %}>
            {{ attributes.text.value }}
        </button>
    ''',
    'modal_message': '''
         <dialog id="{{ attributes.id.value }}" class="modal">
            <div method="dialog" class="modal-box">
                <h3 class="font-bold text-lg">{{ attributes.title.value }}</h3>
                <p class="py-4">{{ attributes.content.value }}</p>
                <div class="modal-action">
                  <form method="dialog">
                    <button class="btn">Close</button>
                  </form>
                </div>
            </div>
        </dialog>
    ''',
    'modal_form': '''
         <dialog id="{{ attributes.id.value }}" class="modal">
            <div method="dialog" class="modal-box">
                <div id="modal-content" class="modal-content">
                <!-- Form content will be loaded here -->
                </div>
            </div>
         </div>
    ''',
    'form_edit': '''
        <!-- templates/edit_form.html -->
        <h2 class="text-xl font-bold mb-4">Edit {{ configs.table_name }}</h2>
        <form id="myForm" hx-post="/edit/{{ configs.table_name }}/{{ configs.id }}" hx-target="#target">
            {% for column in configs.table_config['columns'] %}
            {% if column['is_hidden'] %}
            {% else %}
            <div class="mb-4">
                <label for="{{ column['name'] }}" class="block text-sm font-bold mb-2">
                    {% if column['label'] %}
                    {{ column['label'] }}
                    {% else %}
                    {{ column['name'] }}
                    {% endif %}
                </label>
                {% if column['input_type'] == 'text' %}
                <input type="text" id="{{ column['name'] }}" name="{{ column['name'] }}" value="{{ configs.data[column['name']] }}" {%
                    if column['configs.primary_key'] %}readonly{% endif %}
                    class="shadow appearance-none border rounded w-full py-2 px-3 text-gray-700 leading-tight focus:outline-none focus:shadow-outline">
                {% elif column['input_type'] == 'number' %}
                <input type="number" id="{{ column['name'] }}" name="{{ column['name'] }}" value="{{ configs.data[column['name']] }}" {%
                    if column['configs.primary_key'] %}readonly{% endif %}
                    class="shadow appearance-none border rounded w-full py-2 px-3 text-gray-700 leading-tight focus:outline-none focus:shadow-outline">
                {% elif column['input_type'] == 'date' %}
                <input type="date" id="{{ column['name'] }}" name="{{ column['name'] }}" value="{{ configs.data[column['name']] }}" {%
                    if column['configs.primary_key'] %}readonly{% endif %}
                    class="shadow appearance-none border rounded w-full py-2 px-3 text-gray-700 leading-tight focus:outline-none focus:shadow-outline">
                {% elif column['input_type'] == 'checkbox' %}
                <input type="checkbox" id="{{ column['name'] }}" name="{{ column['name'] }}" {% if configs.data[column['name']]
                    %}checked{% endif %} {% if column['configs.primary_key'] %}disabled{% endif %} class="mr-2 leading-tight">
                {% elif column['input_type'] == 'select' %}
                <select id="{{ column['name'] }}" name="{{ column['name'] }}" {% if column['configs.primary_key'] %}disabled{% endif %}
                    class="shadow appearance-none border rounded w-full py-2 px-3 text-gray-700 leading-tight focus:outline-none focus:shadow-outline">
                    {% for option in column['options'] %}
                    <option value="{{ option }}" {% if configs.data[column['name']]==option %}selected{% endif %}>{{ option }}</option>
                    {% endfor %}
                </select>
                {% endif %}
            </div>
            {% endif %}
            {% endfor %}
            <div class="flex justify-end">
                <button type="button" onclick="hideModal()"
                    class="bg-gray-500 hover:bg-gray-700 text-white font-bold py-2 px-4 rounded focus:outline-none focus:shadow-outline mr-2">Cancel</button>
                <button type="submit"
                    class="bg-blue-500 hover:bg-blue-700 text-white font-bold py-2 px-4 rounded focus:outline-none focus:shadow-outline">Update</button>
            </div>
            <div style="display: none;" id="target"></div>
        </form>

        <script>
            document.getElementById('myForm').addEventListener('htmx:afterRequest', function (evt) {
                console.log('Request completed');
                document.getElementById('btn-table-refresh').click();
                hideModal();
            });
        </script>
    '''
}

# YAML configuration as a Python string
YAML_CONFIG = """
  title: Responsive Dashboard with Drawers
  component_definitions:
    main_navbar:
      id: main_navbar
      type: navbar
      attributes:
        title: 
          type: string
          value: My Dashboard
        class:
          type: string
          value: mb-4
        menu_items:
          type: list
          value:
            - {text: Home, link: "#"}
            - {text: About, link: "#about"}
            - {text: Contact, link: "#contact"}
    
    table_list:
      id: table_list
      type: list
      value: getTables
      
    table_list1:
      id: table_list1
      type: list
      value: getTables1
  
    main_data_table:
      id: main_data_table
      type: data-table
      config: get_configs
      data: get_table_data_params
    
    button:
      id: button
      type: button
      attributes: 
        id:
          type: string
          value: button
        text:
          type: string
          value: ok
        onclick:
          type: string
          value: modal_message.showModal()
          
    modal_message:
      id: modal_message
      type: modal_message
      attributes:
        id:
          type: string
          value: modal_message
        title:
          type: string
          value: modal
        content:
          type: string
          value: aaaaa
          
    modal_form:
      id: modal_form
      type: modal_form
      attributes:
        id:
          type: string
          value: modal_form
        title:
          type: string
          value: modal
        content:
          type: string
          value: aaaaa
          
    form_edit:
      id: form_edit
      type: form_edit
  
    registration_form:
      id: registration_form
      type: form
      attributes:
        class:
          type: string
          value: mt-4 max-w-md mx-auto
        fields:
          type: list
          value:
            - {name: username, type: text, label: Username, placeholder: Enter your username, required: true}
            - {name: email, type: email, label: Email, placeholder: Enter your email, required: true}
            - {name: password, type: password, label: Password, placeholder: Enter your password, required: true}
            - {name: age, type: number, label: Age, placeholder: Enter your age}
            - {name: birthdate, type: date, label: Birth Date}
            - {name: bio, type: textarea, label: Biography, placeholder: Tell us about yourself}
            - name: country
              type: select
              label: Country
              required: true
              options:
                - {value: us, label: United States}
                - {value: uk, label: United Kingdom}
                - {value: ca, label: Canada}
            - name: newsletter
              type: checkbox
              label: Subscribe to newsletter
              checkboxLabel: Yes, I want to receive updates
            - name: gender
              type: radio
              label: Gender
              options:
                - {value: male, label: Male}
                - {value: female, label: Female}
                - {value: other, label: Other}
            - name: profile_picture
              type: file
              label: Profile Picture
              helpText: Please upload an image file (JPG, PNG)
        submit_text:
          type: string
          value: Register
  
  components:
    - $ref: main_navbar
    - type: container
      attributes:
        class:
          type: string
          value: "px-4 py-8"
      children:
        - $ref: button
        - $ref: modal_message
        - $ref: modal_form
        #- $ref: table_list
        - $ref: table_list1
        - $ref: main_data_table
        - $ref: registration_form
        - type: form
          attributes:
            id: 
              type: string
              value: genre
            class:
              type: string
              value: mt-4 max-w-md mx-auto
            fields:
              type: list
              value:
                - {name: GenreId, type: number, label: ジャンルID, placeholder: , required: true, disabled: true}
                - {name: Name, type: text, label: ジャンル名称, placeholder: , required: true, readonly: true}
            submit_text:
              type: string
              value: Register
"""

def load_page_config() -> Dict[str, Any]:
    config = yaml.safe_load(YAML_CONFIG)
    
    # 创建一个组件字典，用于存储预定义的组件
    gv.component_dict = {comp['id']: comp for comp in config.get('component_definitions', {}).values()}
    
    # 递归函数，用于解析组件引用
    def resolve_component(comp):
        if isinstance(comp, dict) and '$ref' in comp:
            return gv.component_dict[comp['$ref']]
        elif isinstance(comp, dict) and 'children' in comp:
            comp['children'] = [resolve_component(child) for child in comp['children']]
        return comp
    
    # 解析所有组件引用
    config['components'] = [resolve_component(comp) for comp in config['components']]
    
    return config
    
def generate_html(component: Dict[str, Any]) -> str:

    for key in ['config', 'data', 'value']:
        if key in component and type(component[key]) is str:
            if globals()[component[key]]:
                component[key] = globals()[component[key]]()

    template = Template(HTML_TEMPLATES.get(component['type'], ''))
    rendered_children = [generate_html(child) for child in component.get('children', [])]
    return template.render(
      attributes=component.get('attributes', {}), 
      configs=component.get('config', {}), 
      data=component.get('data', {}), 
      value=component.get('value', []), 
      children=rendered_children,
      min=min)

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


@app.get("/page", response_class=HTMLResponse)
async def render_page(request: Request):
    gv.request = request

    page_config = load_page_config()
    rendered_components = [generate_html(component) for component in page_config['components']]

    template = Template(BASE_HTML)
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
    
    '''
    rendered_components = [generate_html(gv.component_dict[component_id])]
    #print(rendered_components)
    return rendered_components[0]
    #template = Template(BASE_HTML)
    template = Template('<div></div>')
    return template.render(
        components=rendered_components,
        min=min
    )
    '''


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

@app.get("/create/{table_name}")
async def create_form(request: Request, table_name: str):
    if table_name not in metadata.tables:
        raise HTTPException(status_code=404, detail="Table not found")
    
    table = metadata.tables[table_name]
    columns = [col.name for col in table.columns if col.name != get_primary_key(table)]
    return templates.TemplateResponse("create_form.html", {
        "request": request, 
        "table_name": table_name, 
        "columns": columns,
    })

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

@app.get("/edit1/{table_name}/{id}")
async def edit_form1(request: Request, table_name: str, id: str, page: int = 1, search: str = '', page_size: int = 10):
    if table_name not in metadata.tables:
        raise HTTPException(status_code=404, detail="Table not found")
    
    table_config = get_table_config(table_name)
    
    table = metadata.tables[table_name]
    primary_key = get_primary_key(table)
    
    with SessionLocal() as session:
        stmt = select(table).where(getattr(table.c, primary_key) == id)
        result = session.execute(stmt).fetchone()._asdict()
    
    data = dict(result)
    
    if result:
        return templates.TemplateResponse("edit_form.html", {
            "request": request,
            "table_name": table_name,
            "id": id,
            "item": data,
            "primary_key": primary_key,
            "page": page,
            "page_size": page_size,
            "search": search,
            "table_config": table_config
        })
    raise HTTPException(status_code=404, detail="Item not found")

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
