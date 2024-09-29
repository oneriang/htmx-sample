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
          <script src="https://cdn.jsdelivr.net/gh/alpinejs/alpine@v2.x.x/dist/alpine.min.js" defer></script>
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
    'layout1': '''
        <div class="drawer lg:drawer-open">
            <input id="drawer-left" type="checkbox" class="drawer-toggle" />
            <div class="drawer-content flex flex-col">
                <!-- Navbar -->
                <div class="w-full navbar bg-base-300">
                    <div class="flex-none lg:hidden">
                        <label for="drawer-left" aria-label="open left sidebar" class="btn btn-square btn-ghost">
                            <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" class="inline-block w-6 h-6 stroke-current"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 12h16M4 18h16"></path></svg>
                        </label>
                    </div>
                    <div class="flex-1 px-2 mx-2">Navbar Title</div>
                    <div class="flex-none">
                        <label for="drawer-right" aria-label="open right sidebar" class="btn btn-square btn-ghost">
                            <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" class="inline-block w-6 h-6 stroke-current"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 12h16M4 18h16"></path></svg>
                        </label>
                    </div>
                </div>
                <!-- Page content -->
                <div class="grid mb-4 pb-10 px-8 mx-4 rounded-3xl bg-gray-100 border-4 border-green-400">
                  {% for child in children %}
                      {{ child | safe }}
                  {% endfor %}
                </div>
            </div>
            <!-- Left drawer -->
            <div class="drawer-side">
                <label for="drawer-left" aria-label="close left sidebar" class="drawer-overlay"></label>
                <ul class="menu p-4 w-80 h-full bg-base-200 text-base-content">
                    <li><a>Left Sidebar Item 1</a></li>
                    <li><a>Left Sidebar Item 2</a></li>
                </ul>
            </div>
        </div>

        <!-- Right drawer -->
        <div class="drawer drawer-end">
            <input id="drawer-right" type="checkbox" class="drawer-toggle" />
            <div class="drawer-content">
                <!-- Page content here -->
            </div> 
            <div class="drawer-side">
                <label for="drawer-right" aria-label="close right sidebar" class="drawer-overlay"></label>
                <ul class="menu p-4 w-80 min-h-full bg-base-200 text-base-content">
                    <li><a>Right Sidebar Item 1</a></li>
                    <li><a>Right Sidebar Item 2</a></li>
                </ul>
            </div>
        </div>
      </div>
    ''',
    'layout2': '''
        <div class="drawer lg:drawer-open">
            <input id="drawer-left" type="checkbox" class="drawer-toggle" />
            <div class="drawer-content flex flex-col">
                <!-- Navbar -->
                <div class="w-full navbar bg-base-300">
                    <div class="flex-none lg:hidden">
                        <label for="drawer-left" aria-label="open left sidebar" class="btn btn-square btn-ghost">
                            <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" class="inline-block w-6 h-6 stroke-current"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 12h16M4 18h16"></path></svg>
                        </label>
                    </div>
                    <div class="flex-1 px-2 mx-2">Navbar Title</div>
                    <div class="flex-none">
                        <label for="drawer-right" aria-label="open right sidebar" class="btn btn-square btn-ghost">
                            <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" class="inline-block w-6 h-6 stroke-current"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 12h16M4 18h16"></path></svg>
                        </label>
                    </div>
                </div>
                {% for child in children.generic %}
                    {{ child | safe }}
                {% endfor %}
                <!-- Main content -->
                <div class="grid mb-4 pb-10 px-8 mx-4 rounded-3xl bg-gray-100 border-4 border-green-400">
                    {% for child in children.main_content %}
                        {{ child | safe }}
                    {% endfor %}
                </div>
            </div>
            <!-- Left drawer -->
            <div class="drawer-side">
                <label for="drawer-left" aria-label="close left sidebar" class="drawer-overlay"></label>
                <ul class="menu p-4 w-80 h-full bg-base-200 text-base-content">
                    {% for child in children.left_sidebar %}
                        {{ child | safe }}
                    {% endfor %}
                </ul>
            </div>
        </div>

        <!-- Right drawer -->
        <div class="drawer drawer-end">
            <input id="drawer-right" type="checkbox" class="drawer-toggle" />
            <div class="drawer-content">
                <!-- Page content here -->
                
            </div> 
            <div class="drawer-side">
                <label for="drawer-right" aria-label="close right sidebar" class="drawer-overlay"></label>
                <ul class="menu p-4 w-80 min-h-full bg-base-200 text-base-content">
                    {% for child in children.right_sidebar %}
                        {{ child | safe }}
                    {% endfor %}
                </ul>
            </div>
        </div>
    ''',
    'layout3': '''
        <div class="flex">
            <div class="w-1/4 bg-gray-100">
                {% for child in children.left_sidebar %}
                    {{ child | safe }}
                {% endfor %}
            </div>
            <div class="w-1/2">
                {% for child in children.main_content %}
                    {{ child | safe }}
                {% endfor %}
            </div>
            <div class="w-1/4 bg-gray-100">
                {% for child in children.right_sidebar %}
                    {{ child | safe }}
                {% endfor %}
            </div>
        </div>
        {% for child in children.generic %}
            {{ child | safe }}
        {% endfor %}
    ''',
    'layout': '''
        <div class="drawer lg:drawer-open">
            <input id="drawer-left" type="checkbox" class="drawer-toggle" />
            <div class="drawer-content flex flex-col">
                <!-- Navbar -->
                <div class="w-full navbar bg-base-300">
                    <div class="flex-none">
                        <label for="drawer-left" aria-label="toggle left sidebar" class="btn btn-square btn-ghost lg:hidden">
                            <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" class="inline-block w-6 h-6 stroke-current"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 12h16M4 18h16"></path></svg>
                        </label>
                        <label for="drawer-left" aria-label="toggle left sidebar" class="btn btn-square btn-ghost hidden lg:flex">
                            <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" class="inline-block w-6 h-6 stroke-current"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 12h16M4 18h16"></path></svg>
                        </label>
                    </div>
                    <div class="flex-1 px-2 mx-2">Navbar Title</div>
                    <div class="flex-none">
                        <label for="drawer-right" aria-label="open right sidebar" class="btn btn-square btn-ghost">
                            <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" class="inline-block w-6 h-6 stroke-current"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 12h16M4 18h16"></path></svg>
                        </label>
                    </div>
                </div>
                {% for child in children.generic %}
                    {{ child | safe }}
                {% endfor %}
                <!-- Main content -->
                <div class="grid mb-4 pb-10 px-8 mx-4 rounded-3xl bg-gray-100 border-4 border-green-400">
                    {% for child in children.main_content %}
                        {{ child | safe }}
                    {% endfor %}
                </div>
            </div>
            <!-- Left drawer -->
            <div class="drawer-side">
                <label for="drawer-left" aria-label="close left sidebar" class="drawer-overlay"></label>
                <ul class="menu p-4 w-80 h-full bg-base-200 text-base-content">
                    {% for child in children.left_sidebar %}
                        {{ child | safe }}
                    {% endfor %}
                </ul>
            </div>
        </div>

        <!-- Right drawer -->
        <div class="drawer drawer-end">
            <input id="drawer-right" type="checkbox" class="drawer-toggle" />
            <div class="drawer-content">
                <!-- Page content here -->
            </div> 
            <div class="drawer-side">
                <label for="drawer-right" aria-label="close right sidebar" class="drawer-overlay"></label>
                <ul class="menu p-4 w-80 min-h-full bg-base-200 text-base-content">
                    {% for child in children.right_sidebar %}
                        {{ child | safe }}
                    {% endfor %}
                </ul>
            </div>
        </div>
    ''',
    'drawer_content': '''
        {% for child in children %}
            {{ child | safe }}
        {% endfor %}
    ''',
    'main_content': '''
        {% for child in children %}
            {{ child | safe }}
        {% endfor %}
    ''',
    'container': '''
        <div class="container mx-auto {{ attributes.class.value }}">
          {% for child in children %}
            {{ child | safe }}
          {% endfor %}
        </div>
    ''',
    'card1': '''
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
    'card': '''
        <a class="transform  hover:scale-105 transition duration-300 shadow-xl rounded-lg col-span-12 sm:col-span-6 xl:col-span-3 intro-y bg-white"
                                        href="#">
            <div class="p-5">
                <div class="flex justify-between">
                    <svg xmlns="http://www.w3.org/2000/svg" class="h-7 w-7 text-green-400"
                        fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path stroke-linecap="round" stroke-linejoin="round"
                            stroke-width="2"
                            d="M7 12l3-3 3 3 4-4M8 21l4-4 4 4M3 4h18M4 4h16v12a1 1 0 01-1 1H5a1 1 0 01-1-1V4z" />
                    </svg>
                    <div
                        class="bg-blue-500 rounded-full h-6 px-2 flex justify-items-center text-white font-semibold text-sm">
                        <span class="flex items-center">30%</span>
                    </div>
                </div>
                <div class="ml-2 w-full flex-1">
                    <div>
                        <div class="mt-3 text-3xl font-bold leading-8">4.510</div>

                        <div class="mt-1 text-base text-gray-600">Item Sales</div>
                    </div>
                </div>
            </div>
        </a>
    ''',
    'grid1': '''
        <div class="grid 
            grid-cols-{{ attributes.columns.value if attributes.columns and attributes.columns and attributes.columns.value else '2' }} 
            {{ attributes.class.value if attributes and attributes.class and attributes.class.value }}">
            {% for child in children %}
                <div class="col-span-1">{{ child | safe }}</div>
            {% endfor %}
        </div>
    ''',
    'grid': '''
        <div class="grid grid-cols-12 gap-6">
            <div class="grid grid-cols-12 col-span-12 gap-6 xxl:col-span-9">
                <div class="col-span-12 mt-8">
                    <div class="grid grid-cols-12 gap-6 mt-5">
                        {% for child in children %}
                            {{ child | safe }}
                        {% endfor %}
                    </div>
                </div>
            </div>
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
                          <button hx-get="/create?table_name={{ configs.table_name }}" hx-target="#modal-content"
                              hx-trigger="click" onclick="modal_form.showModal()" class="text-blue-500 hover:underline">Create</button>
                          <button hx-get="/create/{{ configs.table_name }}" hx-target="#modal-content"
                              hx-trigger="click" onclick="modal_form.showModal()" class="text-blue-500 hover:underline">Create</button>
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
                <h3 class="font-bold text-lg">{{ attributes.title.value }}</h3>
                <div id="modal-content" class="modal-content">
                </div>
                <div class="modal-action">
                  <form method="dialog">
                    <button class="btn">Close</button>
                  </form>
                </div>
            </div>
        </dialog>
    ''',
    'form_create': '''
        <!-- templates/edit_form.html -->
        <h2 class="text-xl font-bold mb-4">Create {{ configs.table_name }}</h2>
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
                <input type="text" id="{{ column['name'] }}" name="{{ column['name'] }}"  {%
                    if column['configs.primary_key'] %}readonly{% endif %}
                    class="shadow appearance-none border rounded w-full py-2 px-3 text-gray-700 leading-tight focus:outline-none focus:shadow-outline">
                {% elif column['input_type'] == 'number' %}
                <input type="number" id="{{ column['name'] }}" name="{{ column['name'] }}"  {%
                    if column['configs.primary_key'] %}readonly{% endif %}
                    class="shadow appearance-none border rounded w-full py-2 px-3 text-gray-700 leading-tight focus:outline-none focus:shadow-outline">
                {% elif column['input_type'] == 'date' %}
                <input type="date" id="{{ column['name'] }}" name="{{ column['name'] }}"  {%
                    if column['configs.primary_key'] %}readonly{% endif %}
                    class="shadow appearance-none border rounded w-full py-2 px-3 text-gray-700 leading-tight focus:outline-none focus:shadow-outline">
                {% elif column['input_type'] == 'checkbox' %}
                <input type="checkbox" id="{{ column['name'] }}" name="{{ column['name'] }}" {% if column['configs.primary_key'] %}disabled{% endif %} class="mr-2 leading-tight">
                {% elif column['input_type'] == 'select' %}
                <select id="{{ column['name'] }}" name="{{ column['name'] }}" {% if column['configs.primary_key'] %}disabled{% endif %}
                    class="shadow appearance-none border rounded w-full py-2 px-3 text-gray-700 leading-tight focus:outline-none focus:shadow-outline">
                    {% for option in column['options'] %}
                    <option value="{{ option }}">{{ option }}</option>
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
    ''',
    'alert': '''
        <div role="alert" class="alert {{ attributes.type.value }}">
            <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" class="stroke-current shrink-0 w-6 h-6"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg>
            <span>{{ attributes.message.value }}</span>
        </div>
    ''',
    'progress': '''
        <progress class="progress {{ attributes.color.value }} w-56" value="{{ attributes.value.value }}" max="{{ attributes.max.value }}"></progress>
    ''',
    'badge': '''
        <span class="badge {{ attributes.color.value }}">{{ attributes.text.value }}</span>
    ''',
    'tabs': '''
        <div class="tabs {{ attributes.class.value }}">
            {% for tab in attributes.tabs.value %}
                <a class="tab {{ tab.class }}">{{ tab.text }}</a>
            {% endfor %}
        </div>
    ''',
    'collapse': '''
        <div class="collapse bg-base-200">
            <input type="checkbox" /> 
            <div class="collapse-title text-xl font-medium">
                {{ attributes.title.value }}
            </div>
            <div class="collapse-content"> 
                <p>{{ attributes.content.value }}</p>
            </div>
        </div>
    ''',
    'tooltip': '''
        <div class="tooltip" data-tip="{{ attributes.tip.value }}">
            <button class="btn">{{ attributes.text.value }}</button>
        </div>
    ''',
    'dropdown': '''
        <div class="dropdown">
            <label tabindex="0" class="btn m-1">{{ attributes.label.value }}</label>
            <ul tabindex="0" class="dropdown-content menu p-2 shadow bg-base-100 rounded-box w-52">
                {% for item in attributes.items.value %}
                    <li><a>{{ item }}</a></li>
                {% endfor %}
            </ul>
        </div>
    ''',
    'stat': '''
        <div class="stat">
            <div class="stat-figure text-primary">
                <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" class="inline-block w-8 h-8 stroke-current"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4.318 6.318a4.5 4.5 0 000 6.364L12 20.364l7.682-7.682a4.5 4.5 0 00-6.364-6.364L12 7.636l-1.318-1.318a4.5 4.5 0 00-6.364 0z"></path></svg>
            </div>
            <div class="stat-title">{{ attributes.title.value }}</div>
            <div class="stat-value text-primary">{{ attributes.value.value }}</div>
            <div class="stat-desc">{{ attributes.description.value }}</div>
        </div>
    ''',
    'carousel': '''
        <div class="carousel w-full">
            {% for item in attributes.items.value %}
                <div id="slide{{ loop.index }}" class="carousel-item relative w-full">
                    <img src="{{ item.image }}" class="w-full" alt="Slide {{ loop.index }}">
                    <div class="absolute flex justify-between transform -translate-y-1/2 left-5 right-5 top-1/2">
                        <a href="#slide{{ loop.previtem if loop.previtem else loop.length }}" class="btn btn-circle">❮</a> 
                        <a href="#slide{{ loop.nextitem if loop.nextitem else 1 }}" class="btn btn-circle">❯</a>
                    </div>
                </div>
            {% endfor %}
        </div>
    ''',
    'modal': '''
        <div class="modal" id="{{ attributes.id.value }}">
            <div class="modal-box">
                <h3 class="font-bold text-lg">{{ attributes.title.value }}</h3>
                <p class="py-4">{{ attributes.content.value }}</p>
                <div class="modal-action">
                    <label for="{{ attributes.id.value }}" class="btn">Close</label>
                </div>
            </div>
        </div>
    ''',
    'rating': '''
        <div class="rating">
            {% for i in range(attributes.max.value) %}
                <input type="radio" name="{{ attributes.name.value }}" class="mask mask-star-2 bg-orange-400" {% if i + 1 == attributes.value.value %}checked{% endif %}>
            {% endfor %}
        </div>
    ''',
    'timeline': '''
        <ul class="timeline timeline-vertical">
            {% for item in attributes.items.value %}
                <li>
                    <div class="timeline-start">{{ item.time }}</div>
                    <div class="timeline-middle">
                        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" class="w-5 h-5"><path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.857-9.809a.75.75 0 00-1.214-.882l-3.483 4.79-1.88-1.88a.75.75 0 10-1.06 1.061l2.5 2.5a.75.75 0 001.137-.089l4-5.5z" clip-rule="evenodd" /></svg>
                    </div>
                    <div class="timeline-end timeline-box">{{ item.content }}</div>
                    <hr/>
                </li>
            {% endfor %}
        </ul>
    ''',
    'drawer': '''
        <div class="drawer">
            <input id="{{ attributes.id.value }}" type="checkbox" class="drawer-toggle" />
            <div class="drawer-content">
                <!-- Page content here -->
                <label for="{{ attributes.id.value }}" class="btn btn-primary drawer-button">Open drawer</label>
            </div> 
            <div class="drawer-side">
                <label for="{{ attributes.id.value }}" class="drawer-overlay"></label>
                <ul class="menu p-4 w-80 min-h-full bg-base-200 text-base-content">
                    {% for item in attributes.menu_items.value %}
                        <li><a>{{ item }}</a></li>
                    {% endfor %}
                </ul>
            </div>
        </div>
    ''',
    'steps': '''
        <ul class="steps steps-vertical lg:steps-horizontal">
            {% for step in attributes.steps.value %}
                <li class="step {% if loop.index <= attributes.current_step.value %}step-primary{% endif %}">{{ step }}</li>
            {% endfor %}
        </ul>
    ''',
    'hero': '''
        <div class="hero min-h-screen" style="background-image: url({{ attributes.background_image.value }});">
            <div class="hero-overlay bg-opacity-60"></div>
            <div class="hero-content text-center text-neutral-content">
                <div class="max-w-md">
                    <h1 class="mb-5 text-5xl font-bold">{{ attributes.title.value }}</h1>
                    <p class="mb-5">{{ attributes.description.value }}</p>
                    <button class="btn btn-primary">{{ attributes.button_text.value }}</button>
                </div>
            </div>
        </div>
    ''',
    'chat_bubble': '''
        <div class="chat {% if attributes.position.value == 'end' %}chat-end{% else %}chat-start{% endif %}">
            <div class="chat-image avatar">
                <div class="w-10 rounded-full">
                    <img alt="Avatar" src="{{ attributes.avatar.value }}" />
                </div>
            </div>
            <div class="chat-header">
                {{ attributes.name.value }}
                <time class="text-xs opacity-50">{{ attributes.time.value }}</time>
            </div>
            <div class="chat-bubble">{{ attributes.message.value }}</div>
            <div class="chat-footer opacity-50">
                {{ attributes.footer.value }}
            </div>
        </div>
    ''',
    'stats': '''
        <div class="stats shadow">
            {% for stat in attributes.stats.value %}
            <div class="stat">
                <div class="stat-figure text-{{ stat.color }}">
                    <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" class="inline-block w-8 h-8 stroke-current"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="{{ stat.icon }}"></path></svg>
                </div>
                <div class="stat-title">{{ stat.title }}</div>
                <div class="stat-value text-{{ stat.color }}">{{ stat.value }}</div>
                <div class="stat-desc">{{ stat.desc }}</div>
            </div>
            {% endfor %}
        </div>
    ''',
    'file_input': '''
        <div class="form-control w-full max-w-xs">
            <label class="label">
                <span class="label-text">{{ attributes.label.value }}</span>
            </label>
            <input type="file" class="file-input file-input-bordered w-full max-w-xs" />
        </div>
    ''',
    'code': '''
        <div class="mockup-code">
            {% for line in attributes.code.value.split('\n') %}
            <pre data-prefix="{{ loop.index }}"><code>{{ line }}</code></pre>
            {% endfor %}
        </div>
    ''',
    'breadcrumbs': '''
        <div class="text-sm breadcrumbs">
            <ul>
                {% for item in attributes.items.value %}
                <li><a href="{{ item.link }}">{{ item.text }}</a></li>
                {% endfor %}
            </ul>
        </div>
    ''',
    'menu': '''
        <ul class="menu bg-base-200 w-56 rounded-box">
            {% for item in attributes.items.value %}
            <li>
                {% if item.submenu %}
                <details open>
                    <summary>{{ item.text }}</summary>
                    <ul>
                        {% for subitem in item.submenu %}
                        <li><a href="{{ subitem.link }}">{{ subitem.text }}</a></li>
                        {% endfor %}
                    </ul>
                </details>
                {% else %}
                <a href="{{ item.link }}">{{ item.text }}</a>
                {% endif %}
            </li>
            {% endfor %}
        </ul>
    ''',
    'radial_progress': '''
        <div class="radial-progress text-primary" style="--value:{{ attributes.value.value }};">{{ attributes.value.value }}%</div>
    ''',
    'skeleton': '''
        <div class="skeleton w-{{ attributes.width.value }} h-{{ attributes.height.value }}"></div>
    ''',
    'alert_dialog': '''
        <input type="checkbox" id="{{ attributes.id.value }}" class="modal-toggle" />
        <div class="modal">
            <div class="modal-box">
                <h3 class="font-bold text-lg">{{ attributes.title.value }}</h3>
                <p class="py-4">{{ attributes.content.value }}</p>
                <div class="modal-action">
                    <label for="{{ attributes.id.value }}" class="btn btn-primary">Confirm</label>
                    <label for="{{ attributes.id.value }}" class="btn">Cancel</label>
                </div>
            </div>
        </div>
    ''',
    'artboard': '''
        <div class="artboard artboard-demo">
            <div class="text-4xl font-bold">{{ attributes.text.value }}</div>
        </div>
    ''',
    'btn': '''
        <button hx-get="/create?table_name=Yuangong" hx-target="#modal-content"
                              hx-trigger="click" onclick="modal_form.showModal()" class="text-blue-500 hover:underline">Edit</button>
                          
    '''
}

# YAML configuration as a Python string
YAML_CONFIG = """
  title: Responsive Dashboard with Drawers
  component_definitions:
    main_layout:
      id: main_layout
      type: layout
      children:
        generic:
          - type: btn
        left_sidebar:
          - $ref: table_list1
        main_content:
          - $ref: main_data_table
          - type: file_input
            attributes:
              label:
                type: string
                value: "Upload file"
        right_sidebar:
          - $ref: table_list
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
          
    form_create:
      id: form_create
      type: form_create

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
  
  components1:
    - type: layout
      children:
      # - $ref: main_navbar
      - type: container
        attributes:
          class:
            type: string
            value: "px-4 py-8"
        children:
          - $ref: modal_message
          - $ref: modal_form
          - $ref: table_list1
          - $ref: main_data_table
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
  components2:
    - type: layout
      children:
        - type: grid
          children:
            - type: card
            - type: card
            - type: card
            - type: card
        - type: btn
        - $ref: table_list1
        #- $ref: registration_form
        - $ref: main_data_table
        - $ref: modal_form
        - type: alert
          attributes:
            type:
              type: string
              value: alert-info
            message:
              type: string
              value: This is an informational message.
        - type: progress
          attributes:
            color:
              type: string
              value: progress-primary
            value:
              type: number
              value: 70
            max:
              type: number
              value: 100
        - type: stat
          attributes:
            title:
              type: string
              value: Total Likes
            value:
              type: string
              value: 25.6K
            description:
              type: string
              value: 21% more than last month
        - type: stats
          attributes:
            stats:
              type: list
              value:
                - {color: "primary", icon: "M13 10V3L4 14h7v7l9-11h-7z", title: "Downloads", value: "31K", desc: "Jan 1st - Feb 1st"}
                - {color: "secondary", icon: "M12 4.5v15m7.5-7.5h-15", title: "New Users", value: "4,200", desc: "↗︎ 400 (22%)"}
                - {color: "accent", icon: "M3 13.125C3 12.504 3.504 12 4.125 12h2.25c.621 0 1.125.504 1.125 1.125v6.75C7.5 20.496 6.996 21 6.375 21h-2.25A1.125 1.125 0 013 19.875v-6.75z", title: "New Registers", value: "1,200", desc: "↘︎ 90 (14%)"}
        - type: file_input
          attributes:
            label:
              type: string
              value: "Upload file"
        - type: code
          attributes:
            code:
              type: string
              value: |
                def hello_world():
                    print("Hello, World!")
                
                hello_world()
        - type: breadcrumbs
          attributes:
            items:
              type: list
              value:
                - {text: "Home", link: "/"}
                - {text: "Library", link: "/library"}
                - {text: "Data", link: "/library/data"}
        - type: menu
          attributes:
            items:
              type: list
              value:
                - {text: "Home", link: "/"}
                - text: "Categories"
                  submenu:
                    - {text: "Science", link: "/category/science"}
                    - {text: "Art", link: "/category/art"}
                - {text: "About", link: "/about"}
        - type: radial_progress
          attributes:
            value:
              type: number
              value: 70
        - type: skeleton
          attributes:
            width:
              type: string
              value: "32"
            height:
              type: string
              value: "32"
        - type: alert_dialog
          attributes:
            id:
              type: string
              value: "confirm-dialog"
            title:
              type: string
              value: "Are you sure?"
            content:
              type: string
              value: "Do you want to delete this item? This action cannot be undone."
        - type: artboard
          attributes:
            text:
              type: string
              value: "Design Preview"
        - type: carousel
          attributes:
            items:
              type: list
              value:
                - {image: "/image1.jpg"}
                - {image: "/image2.jpg"}
                - {image: "/image3.jpg"}
        - type: modal
          attributes:
            id:
              type: string
              value: my-modal
            title:
              type: string
              value: Important Information
            content:
              type: string
              value: This is some important content that needs attention.
        - type: rating
          attributes:
            name:
              type: string
              value: product-rating
            max:
              type: number
              value: 5
            value:
              type: number
              value: 4
        - type: hero
          attributes:
            background_image:
              type: string
              value: "/hero-bg.jpg"
            title:
              type: string
              value: Welcome to Our App
            description:
              type: string
              value: Discover amazing features and possibilities.
            button_text:
              type: string
              value: Get Started
        - type: chat_bubble
          attributes:
            position:
              type: string
              value: start
            avatar:
              type: string
              value: "/avatar.jpg"
            name:
              type: string
              value: John Doe
            time:
              type: string
              value: "12:45"
            message:
              type: string
              value: Hello, how can I help you today?
            footer:
              type: string
              value: Delivered
  components3:
    - type: layout
      children:
        #- type: drawer_content
        #  children:
        #    - $ref: table_list1
        - type: main_content
          children:
            - type: btn
  components:
    - $ref: main_layout
"""
    
def load_page_config1() -> Dict[str, Any]:
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
    
def generate_html1(component: Dict[str, Any]) -> str:

    for key in ['config', 'data', 'value']:
        if key in component and type(component[key]) is str:
            if globals()[component[key]]:
                component[key] = globals()[component[key]]()

    print(HTML_TEMPLATES.get(component['type'], ''))

    template = Template(HTML_TEMPLATES.get(component['type'], ''))
    rendered_children = [generate_html(child) for child in component.get('children', [])]
    return template.render(
      attributes=component.get('attributes', {}), 
      configs=component.get('config', {}), 
      data=component.get('data', {}), 
      value=component.get('value', []), 
      children=rendered_children,
      min=min)

def generate_html2(component: Dict[str, Any]) -> str:
    # 处理动态函数调用
    for key in ['config', 'data', 'value']:
        if key in component and isinstance(component[key], str):
            if component[key] in globals() and callable(globals()[component[key]]):
                component[key] = globals()[component[key]]()

    # 获取组件类型对应的模板
    template = Template(HTML_TEMPLATES.get(component['type'], ''))

    # 递归处理所有子组件
    rendered_children = [generate_html(child) for child in component.get('children', [])]

    # 准备渲染上下文
    context = {
        'attributes': component.get('attributes', {}),
        'configs': component.get('config', {}),
        'data': component.get('data', {}),
        'value': component.get('value', []),
        'children': rendered_children,
        'min': min  # 如果模板中需要使用 min 函数
    }

    # 渲染模板
    return template.render(**context)

def generate_html3(component: Dict[str, Any]) -> str:
    for key in ['config', 'data', 'value']:
        if key in component and type(component[key]) is str:
            if globals()[component[key]]:
                component[key] = globals()[component[key]]()

    template = Template(HTML_TEMPLATES.get(component['type'], ''))
    
    # 处理特殊的drawer_content和main_content组件
    if component['type'] in ['drawer_content', 'main_content']:
        rendered_children = [generate_html(child) for child in component.get('children', [])]
        return template.render(children=rendered_children)
    
    # 对于layout组件，我们需要分别处理drawer_content和main_content
    elif component['type'] == 'layout':
        drawer_content = next((generate_html(child) for child in component.get('children', []) if child['type'] == 'drawer_content'), '')
        main_content = next((generate_html(child) for child in component.get('children', []) if child['type'] == 'main_content'), '')
        return template.render(drawer_content=drawer_content, main_content=main_content)
    
    # 对于其他组件，保持原有的处理方式
    else:
        rendered_children = [generate_html(child) for child in component.get('children', [])]
        return template.render(
            attributes=component.get('attributes', {}), 
            configs=component.get('config', {}), 
            data=component.get('data', {}), 
            value=component.get('value', []), 
            children=rendered_children,
            min=min)

def load_page_config2() -> Dict[str, Any]:
    config = yaml.safe_load(YAML_CONFIG)
    
    # 创建一个组件字典，用于存储预定义的组件
    gv.component_dict = {comp['id']: comp for comp in config.get('component_definitions', {}).values()}
    
    # 递归函数，用于解析组件引用
    def resolve_component(comp):
        if isinstance(comp, dict):
            if '$ref' in comp:
                return gv.component_dict[comp['$ref']]
            elif 'children' in comp:
                comp['children'] = [resolve_component(child) for child in comp['children']]
        return comp
    
    # 解析所有组件引用
    config['components'] = [resolve_component(comp) for comp in config['components']]
    
    return config
    
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


@app.get("/page1", response_class=HTMLResponse)
async def render_page1(request: Request):
    gv.request = request

    page_config = load_page_config()
    rendered_components = [generate_html(component) for component in page_config['components']]

    template = Template(BASE_HTML)
    return template.render(
        page_title=page_config['title'],
        components=rendered_components,
        min=min
    )

# # 修改 YAML 配置结构示例
# YAML_CONFIG = """
# title: Responsive Dashboard with Flexible Layout
# component_definitions:
#   main_layout:
#     id: main_layout
#     type: layout
#     children:
#       left_sidebar:
#         - $ref: table_list
#       main_content:
#         - $ref: main_data_table
#       right_sidebar:
#         - $ref: registration_form
#       - type: file_input
#         attributes:
#           label:
#             type: string
#             value: "Upload file"
#       - $ref: btn

#   # ... other component definitions ...

# components:
#   - $ref: main_layout

# # ... rest of the YAML configuration ...
# """

# # 修改 HTML 模板
# HTML_TEMPLATES = {
#     'layout': '''
#         <div class="flex">
#             <div class="w-1/4 bg-gray-100">
#                 {% for child in children.left_sidebar %}
#                     {{ child | safe }}
#                 {% endfor %}
#             </div>
#             <div class="w-1/2">
#                 {% for child in children.main_content %}
#                     {{ child | safe }}
#                 {% endfor %}
#             </div>
#             <div class="w-1/4 bg-gray-100">
#                 {% for child in children.right_sidebar %}
#                     {{ child | safe }}
#                 {% endfor %}
#             </div>
#         </div>
#         {% for child in children._unnamed %}
#             {{ child | safe }}
#         {% endfor %}
#     ''',
#     # ... other templates ...
# }

# 修改渲染函数
def generate_html(component: Dict[str, Any]) -> str:
    for key in ['config', 'data', 'value']:
        if key in component and isinstance(component[key], str):
            if component[key] in globals():
                component[key] = globals()[component[key]]()

    template = Template(HTML_TEMPLATES.get(component['type'], ''))
    
    rendered_children = {'_unnamed': []}
    if 'children' in component:
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
    config = yaml.safe_load(YAML_CONFIG)
    
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
