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

BASE_HTML3 = '''
<!-- component -->
<!DOCTYPE html>
<html x-data="data()" lang="en">

<head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap"
        rel="stylesheet" />
    <!-- Favicon -->
    <script src="https://cdn.jsdelivr.net/gh/alpinejs/alpine@v2.x.x/dist/alpine.min.js" defer></script>
    <script src="https://cdn.tailwindcss.com"></script>
    <script src="https://unpkg.com/htmx.org@1.9.2"></script>
      
</head>

<body>
    <div class="flex h-screen bg-gray-800 " :class="{ 'overflow-hidden': isSideMenuOpen }">

        <!-- Desktop sidebar -->
        <aside class="z-20 flex-shrink-0 hidden w-60 pl-2 overflow-y-auto bg-gray-800 md:block">
            <div>
                <div class="text-white">
                    <div class="flex p-2  bg-gray-800">
                        <div class="flex py-3 px-2 items-center">
                            <p class="text-2xl text-green-500 font-semibold">SA</p <p class="ml-2 font-semibold italic">
                            DASHBOARD</p>
                        </div>
                    </div>
                    <div class="flex justify-center">
                        <div class="">
                            <img class="hidden h-24 w-24 rounded-full sm:block object-cover mr-2 border-4 border-green-400"
                                src="https://image.flaticon.com/icons/png/512/149/149071.png" alt="">
                            <p class="font-bold text-base  text-gray-400 pt-2 text-center w-24">Safwan</p>
                        </div>
                    </div>
                    <div>
                        <ul class="mt-6 leading-10">
                            <li class="relative px-2 py-1 ">
                                <a class="inline-flex items-center w-full text-sm font-semibold text-white transition-colors duration-150 cursor-pointer hover:text-green-500" 
                                    href=" #">
                                    <svg xmlns="http://www.w3.org/2000/svg" class="h-6 w-6" fill="none"
                                        viewBox="0 0 24 24" stroke="currentColor">
                                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                                            d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6" />
                                    </svg>
                                    <span class="ml-4">DASHBOARD</span>
                                </a>
                            </li>
                            <li class="relative px-2 py-1" x-data="{ Open : false  }">
                                <div class="inline-flex items-center justify-between w-full text-base font-semibold transition-colors duration-150 text-gray-500  hover:text-yellow-400 cursor-pointer"
                                    x-on:click="Open = !Open">
                                    <span
                                        class="inline-flex items-center  text-sm font-semibold text-white hover:text-green-400">
                                        <svg xmlns="http://www.w3.org/2000/svg" class="h-6 w-6" fill="none"
                                            viewBox="0 0 24 24" stroke="currentColor">
                                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                                                d="M8 4H6a2 2 0 00-2 2v12a2 2 0 002 2h12a2 2 0 002-2V6a2 2 0 00-2-2h-2m-4-1v8m0 0l3-3m-3 3L9 8m-5 5h2.586a1 1 0 01.707.293l2.414 2.414a1 1 0 00.707.293h3.172a1 1 0 00.707-.293l2.414-2.414a1 1 0 01.707-.293H20" />
                                        </svg>
                                        <span class="ml-4">ITEM</span>
                                    </span>
                                    <svg xmlns="http://www.w3.org/2000/svg" x-show="!Open"
                                        class="ml-1  text-white w-4 h-4" fill="none" viewBox="0 0 24 24"
                                        stroke="currentColor" style="display: none;">
                                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                                            d="M15 19l-7-7 7-7" />
                                    </svg>

                                    <svg xmlns="http://www.w3.org/2000/svg" x-show="Open"
                                        class="ml-1  text-white w-4 h-4" fill="none" viewBox="0 0 24 24"
                                        stroke="currentColor" style="display: none;">
                                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                                            d="M19 9l-7 7-7-7" />
                                    </svg>
                                </div>

                                <div x-show.transition="Open" style="display:none;">
                                    <ul x-transition:enter="transition-all ease-in-out duration-300"
                                        x-transition:enter-start="opacity-25 max-h-0"
                                        x-transition:enter-end="opacity-100 max-h-xl"
                                        x-transition:leave="transition-all ease-in-out duration-300"
                                        x-transition:leave-start="opacity-100 max-h-xl"
                                        x-transition:leave-end="opacity-0 max-h-0"
                                        class="p-2 mt-2 space-y-2 overflow-hidden text-sm font-medium  rounded-md shadow-inner  bg-green-400"
                                        aria-label="submenu">

                                        <li class="px-2 py-1 text-white transition-colors duration-150">
                                            <div class="px-1 hover:text-gray-800 hover:bg-gray-100 rounded-md">
                                                <div class="flex items-center">
                                                    <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" fill="none"
                                                        viewBox="0 0 24 24" stroke="currentColor">
                                                        <path stroke-linecap="round" stroke-linejoin="round"
                                                            stroke-width="2"
                                                            d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6" />
                                                    </svg>
                                                    <a href="#"
                                                        class="w-full ml-2  text-sm font-semibold text-white hover:text-gray-800">Item
                                                        1</a>
                                                </div>
                                            </div>
                                        </li>
                                    </ul>
                                </div>
                            </li>
                        </ul>
                    </div>
                </div>
            </div>
        </aside>

        <!-- Mobile sidebar -->
        <!-- Backdrop -->
        <div x-show="isSideMenuOpen" x-transition:enter="transition ease-in-out duration-150"
            x-transition:enter-start="opacity-0" x-transition:enter-end="opacity-100"
            x-transition:leave="transition ease-in-out duration-150" x-transition:leave-start="opacity-100"
            x-transition:leave-end="opacity-0"
            class="fixed inset-0 z-10 flex items-end bg-black bg-opacity-50 sm:items-center sm:justify-center"></div>

        <aside
            class="fixed inset-y-0 z-20 flex-shrink-0 w-64 mt-16 overflow-y-auto  bg-gray-900 dark:bg-gray-800 md:hidden"
            x-show="isSideMenuOpen" x-transition:enter="transition ease-in-out duration-150"
            x-transition:enter-start="opacity-0 transform -translate-x-20" x-transition:enter-end="opacity-100"
            x-transition:leave="transition ease-in-out duration-150" x-transition:leave-start="opacity-100"
            x-transition:leave-end="opacity-0 transform -translate-x-20" @click.away="closeSideMenu"
            @keydown.escape="closeSideMenu">
            <div>
                <div class="text-white">
                    <div class="flex p-2  bg-gray-800">
                        <div class="flex py-3 px-2 items-center">
                            <p class="text-2xl text-green-500 font-semibold">SA</p <p class="ml-2 font-semibold italic">
                            DASHBOARD</p>
                        </div>
                    </div>
                    <div>
                        <ul class="mt-6 leading-10">
                            <li class="relative px-2 py-1 ">
                                <a class="inline-flex items-center w-full text-sm font-semibold text-white transition-colors duration-150 cursor-pointer hover:text-green-500"
                                    href=" #">
                                    <svg xmlns="http://www.w3.org/2000/svg" class="h-6 w-6" fill="none"
                                        viewBox="0 0 24 24" stroke="currentColor">
                                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                                            d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6" />
                                    </svg>
                                    <span class="ml-4">DASHBOARD</span>
                                </a>
                            </li>
                            <li class="relative px-2 py-1" x-data="{ Open : false  }">
                                <div class="inline-flex items-center justify-between w-full text-base font-semibold transition-colors duration-150 text-gray-500  hover:text-yellow-400 cursor-pointer"
                                    x-on:click="Open = !Open">
                                    <span
                                        class="inline-flex items-center  text-sm font-semibold text-white hover:text-green-400">
                                        <svg xmlns="http://www.w3.org/2000/svg" class="h-6 w-6" fill="none"
                                            viewBox="0 0 24 24" stroke="currentColor">
                                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                                                d="M8 4H6a2 2 0 00-2 2v12a2 2 0 002 2h12a2 2 0 002-2V6a2 2 0 00-2-2h-2m-4-1v8m0 0l3-3m-3 3L9 8m-5 5h2.586a1 1 0 01.707.293l2.414 2.414a1 1 0 00.707.293h3.172a1 1 0 00.707-.293l2.414-2.414a1 1 0 01.707-.293H20" />
                                        </svg>
                                        <span class="ml-4">ITEM</span>
                                    </span>
                                    <svg xmlns="http://www.w3.org/2000/svg" x-show="!Open"
                                        class="ml-1  text-white w-4 h-4" fill="none" viewBox="0 0 24 24"
                                        stroke="currentColor" style="display: none;">
                                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                                            d="M15 19l-7-7 7-7" />
                                    </svg>

                                    <svg xmlns="http://www.w3.org/2000/svg" x-show="Open"
                                        class="ml-1  text-white w-4 h-4" fill="none" viewBox="0 0 24 24"
                                        stroke="currentColor" style="display: none;">
                                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                                            d="M19 9l-7 7-7-7" />
                                    </svg>
                                </div>

                                <div x-show.transition="Open" style="display:none;">
                                    <ul x-transition:enter="transition-all ease-in-out duration-300"
                                        x-transition:enter-start="opacity-25 max-h-0"
                                        x-transition:enter-end="opacity-100 max-h-xl"
                                        x-transition:leave="transition-all ease-in-out duration-300"
                                        x-transition:leave-start="opacity-100 max-h-xl"
                                        x-transition:leave-end="opacity-0 max-h-0"
                                        class="p-2 mt-2 space-y-2 overflow-hidden text-sm font-medium  rounded-md shadow-inner  bg-green-400"
                                        aria-label="submenu">

                                        <li class="px-2 py-1 text-white transition-colors duration-150">
                                            <div class="px-1 hover:text-gray-800 hover:bg-gray-100 rounded-md">
                                                <div class="flex items-center">
                                                    <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" fill="none"
                                                        viewBox="0 0 24 24" stroke="currentColor">
                                                        <path stroke-linecap="round" stroke-linejoin="round"
                                                            stroke-width="2"
                                                            d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6" />
                                                    </svg>
                                                    <a href="#"
                                                        class="w-full ml-2  text-sm font-semibold text-white hover:text-gray-800">Item
                                                        1</a>
                                                </div>
                                            </div>
                                        </li>
                                    </ul>
                                </div>
                            </li>
                        </ul>
                    </div>
                </div>
            </div>
        </aside>

        <div class="flex flex-col flex-1 w-full overflow-y-auto">
            <header class="z-40 py-4  bg-gray-800  ">
                <div class="flex items-center justify-between h-8 px-6 mx-auto">
                    <!-- Mobile hamburger -->
                    <button class="p-1 mr-5 -ml-1 rounded-md md:hidden focus:outline-none focus:shadow-outline-purple"
                        @click="toggleSideMenu" aria-label="Menu">
                        <x-heroicon-o-menu class="w-6 h-6 text-white" />
                        <svg xmlns="http://www.w3.org/2000/svg" class="w-6 h-6 text-white" fill="none"
                            viewBox="0 0 24 24" stroke="currentColor">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                                d="M4 6h16M4 12h16M4 18h7" />
                        </svg>
                    </button>

                    <!-- Search Input -->
                    <div class="flex justify-center  mt-2 mr-4">
                        <div class="relative flex w-full flex-wrap items-stretch mb-3">
                            <input type="search" placeholder="Search"
                                class="form-input px-3 py-2 placeholder-gray-400 text-gray-700 relative bg-white rounded-lg text-sm shadow outline-none focus:outline-none focus:shadow-outline w-full pr-10" />
                            <span
                                class="z-10 h-full leading-snug font-normal  text-center text-gray-400 absolute bg-transparent rounded text-base items-center justify-center w-8 right-0 pr-3 py-3">
                                <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5 -mt-1" fill="none"
                                    viewBox="0 0 24 24" stroke="currentColor">
                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                                        d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                                </svg>
                            </span>
                        </div>
                    </div>

                    <ul class="flex items-center flex-shrink-0 space-x-6">

                        <!-- Notifications menu -->
                        <li class="relative">
                            <button
                                class="p-2 bg-white text-green-400 align-middle rounded-full hover:text-white hover:bg-green-400 focus:outline-none "
                                @click="toggleNotificationsMenu" @keydown.escape="closeNotificationsMenu"
                                aria-label="Notifications" aria-haspopup="true">
                                <div class="flex items-cemter">
                                    <svg xmlns="http://www.w3.org/2000/svg" class="h-6 w-6" fill="none"
                                        viewBox="0 0 24 24" stroke="currentColor">
                                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                                            d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9" />
                                    </svg>
                                </div>
                                <!-- Notification badge -->
                                <span aria-hidden="true"
                                    class="absolute top-0 right-0 inline-block w-3 h-3 transform translate-x-1 -translate-y-1 bg-red-600 border-2 border-white rounded-full dark:border-gray-800"></span>
                            </button>
                            <template x-if="isNotificationsMenuOpen">
                                <ul x-transition:leave="transition ease-in duration-150"
                                    x-transition:leave-start="opacity-100" x-transition:leave-end="opacity-0"
                                    @click.away="closeNotificationsMenu" @keydown.escape="closeNotificationsMenu"
                                    class="absolute right-0 w-56 p-2 mt-2 space-y-2 text-gray-600 bg-green-400 border border-green-500 rounded-md shadow-md">
                                    <li class="flex">
                                        <a class="text-white inline-flex items-center justify-between w-full px-2 py-1 text-sm font-semibold transition-colors duration-150 rounded-md hover:bg-gray-100 hover:text-gray-800"
                                            href="#">
                                            <span>Messages</span>
                                            <span
                                                class="inline-flex items-center justify-center px-2 py-1 text-xs font-bold leading-none text-red-600 bg-red-100 rounded-full dark:text-red-100 dark:bg-red-600">
                                                13
                                            </span>
                                        </a>
                                    </li>
                                </ul>
                            </template>
                        </li>

                        <!-- Profile menu -->
                        <li class="relative">
                            <button
                                class="p-2 bg-white text-green-400 align-middle rounded-full hover:text-white hover:bg-green-400 focus:outline-none "
                                @click="toggleProfileMenu" @keydown.escape="closeProfileMenu" aria-label="Account"
                                aria-haspopup="true">
                                <div class="flex items-center">
                                    <svg xmlns="http://www.w3.org/2000/svg" class="h-6 w-6" fill="none"
                                        viewBox="0 0 24 24" stroke="currentColor">
                                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                                            d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
                                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                                            d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                                    </svg>
                                </div>
                            </button>
                            <template x-if="isProfileMenuOpen">
                                <ul x-transition:leave="transition ease-in duration-150"
                                    x-transition:leave-start="opacity-100" x-transition:leave-end="opacity-0"
                                    @click.away="closeProfileMenu" @keydown.escape="closeProfileMenu"
                                    class="absolute right-0 w-56 p-2 mt-2 space-y-2 text-gray-600 bg-green-400 border border-green-500 rounded-md shadow-md"
                                    aria-label="submenu">
                                    <li class="flex">
                                        <a class=" text-white inline-flex items-center w-full px-2 py-1 text-sm font-semibold transition-colors duration-150 rounded-md hover:bg-gray-100 hover:text-gray-800"
                                            href="#">
                                            <svg xmlns="http://www.w3.org/2000/svg" class="w-5 h-5 mr-2" fill="none"
                                                viewBox="0 0 24 24" stroke="currentColor">
                                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                                                    d="M5.121 17.804A13.937 13.937 0 0112 16c2.5 0 4.847.655 6.879 1.804M15 10a3 3 0 11-6 0 3 3 0 016 0zm6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                                            </svg>
                                            <span>Profile</span>
                                        </a>
                                    </li>
                                    <li class="flex">
                                        <a class="text-white inline-flex items-center w-full px-2 py-1 text-sm font-semibold transition-colors duration-150 rounded-md hover:bg-gray-100 hover:text-gray-800"
                                            href="#">
                                            <svg xmlns="http://www.w3.org/2000/svg" class="w-5 h-5 mr-2" fill="none"
                                                viewBox="0 0 24 24" stroke="currentColor">
                                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                                                    d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" />
                                            </svg>
                                            <span>Log out</span>
                                        </a>
                                    </li>
                                </ul>
                            </template>
                        </li>
                    </ul>

                </div>
            </header>
            <main class="">
            
                <div class="grid mb-4 pb-10 px-8 mx-4 rounded-3xl bg-gray-100 border-4 border-green-400">
{% for component in components %}
        {{ component | safe }}
    {% endfor %}
                    <div class="grid grid-cols-12 gap-6">
                        <div class="grid grid-cols-12 col-span-12 gap-6 xxl:col-span-9">
                            <div class="col-span-12 mt-8">
                                <div class="flex items-center h-10 intro-y">
                                    <h2 class="mr-5 text-lg font-medium truncate">Dashboard</h2>
                                </div>
                                <div class="grid grid-cols-12 gap-6 mt-5">
                                    <a class="transform  hover:scale-105 transition duration-300 shadow-xl rounded-lg col-span-12 sm:col-span-6 xl:col-span-3 intro-y bg-white"
                                        href="#">
                                        <div class="p-5">
                                            <div class="flex justify-between">
                                                <svg xmlns="http://www.w3.org/2000/svg" class="h-7 w-7 text-blue-400"
                                                    fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                                    <path stroke-linecap="round" stroke-linejoin="round"
                                                        stroke-width="2"
                                                        d="M16 11V7a4 4 0 00-8 0v4M5 9h14l1 12H4L5 9z" />
                                                </svg>
                                                <div
                                                    class="bg-green-500 rounded-full h-6 px-2 flex justify-items-center text-white font-semibold text-sm">
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
                                    <a class="transform  hover:scale-105 transition duration-300 shadow-xl rounded-lg col-span-12 sm:col-span-6 xl:col-span-3 intro-y bg-white"
                                        href="#">
                                        <div class="p-5">
                                            <div class="flex justify-between">
                                                <svg xmlns="http://www.w3.org/2000/svg" class="h-7 w-7 text-yellow-400"
                                                    fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                                    <path stroke-linecap="round" stroke-linejoin="round"
                                                        stroke-width="2"
                                                        d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
                                                </svg>
                                                <div
                                                    class="bg-red-500 rounded-full h-6 px-2 flex justify-items-center text-white font-semibold text-sm">
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
                                    <a class="transform  hover:scale-105 transition duration-300 shadow-xl rounded-lg col-span-12 sm:col-span-6 xl:col-span-3 intro-y bg-white"
                                        href="#">
                                        <div class="p-5">
                                            <div class="flex justify-between">
                                                <svg xmlns="http://www.w3.org/2000/svg" class="h-7 w-7 text-pink-600"
                                                    fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                                    <path stroke-linecap="round" stroke-linejoin="round"
                                                        stroke-width="2"
                                                        d="M11 3.055A9.001 9.001 0 1020.945 13H11V3.055z" />
                                                    <path stroke-linecap="round" stroke-linejoin="round"
                                                        stroke-width="2"
                                                        d="M20.488 9H15V3.512A9.025 9.025 0 0120.488 9z" />
                                                </svg>
                                                <div
                                                    class="bg-yellow-500 rounded-full h-6 px-2 flex justify-items-center text-white font-semibold text-sm">
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
                                </div>
                            </div>
                            <div class="col-span-12 mt-5">
                                <div class="grid gap-2 grid-cols-1 lg:grid-cols-2">
                                    <div class="bg-white shadow-lg p-4" id="chartline"></div>
                                    <div class="bg-white shadow-lg" id="chartpie"></div>
                                </div>
                            </div>
                            <div class="col-span-12 mt-5">
                                <div class="grid gap-2 grid-cols-1 lg:grid-cols-1">
                                    <div class="bg-white p-4 shadow-lg rounded-lg">
                                        <h1 class="font-bold text-base">Table</h1>
                                        <div class="mt-4">
                                            <div class="flex flex-col">
                                                <div class="-my-2 overflow-x-auto">
                                                    <div class="py-2 align-middle inline-block min-w-full">
                                                        <div
                                                            class="shadow overflow-hidden border-b border-gray-200 sm:rounded-lg bg-white">
                                                            <table class="min-w-full divide-y divide-gray-200">
                                                                <thead>
                                                                    <tr>
                                                                        <th
                                                                            class="px-6 py-3 bg-gray-50 text-xs leading-4 font-medium text-gray-500 uppercase tracking-wider">
                                                                            <div class="flex cursor-pointer">
                                                                                <span class="mr-2">PRODUCT NAME</span>
                                                                            </div>
                                                                        </th>
                                                                        <th
                                                                            class="px-6 py-3 bg-gray-50 text-xs leading-4 font-medium text-gray-500 uppercase tracking-wider">
                                                                            <div class="flex cursor-pointer">
                                                                                <span class="mr-2">Stock</span>
                                                                            </div>
                                                                        </th>
                                                                        <th
                                                                            class="px-6 py-3 bg-gray-50 text-xs leading-4 font-medium text-gray-500 uppercase tracking-wider">
                                                                            <div class="flex cursor-pointer">
                                                                                <span class="mr-2">STATUS</span>
                                                                            </div>
                                                                        </th>
                                                                        <th
                                                                            class="px-6 py-3 bg-gray-50 text-xs leading-4 font-medium text-gray-500 uppercase tracking-wider">
                                                                            <div class="flex cursor-pointer">
                                                                                <span class="mr-2">ACTION</span>
                                                                            </div>
                                                                        </th>
                                                                    </tr>
                                                                </thead>
                                                                <tbody class="bg-white divide-y divide-gray-200">
                                                                    <tr>
                                                                        <td
                                                                            class="px-6 py-4 whitespace-no-wrap text-sm leading-5">
                                                                            <p>Apple MacBook Pro 13</p>
                                                                            <p class="text-xs text-gray-400">PC & Laptop
                                                                            </p>
                                                                        </td>
                                                                        <td
                                                                            class="px-6 py-4 whitespace-no-wrap text-sm leading-5">
                                                                            <p>77</p>
                                                                        </td>
                                                                        <td
                                                                            class="px-6 py-4 whitespace-no-wrap text-sm leading-5">
                                                                            <div class="flex text-green-500">
                                                                                <svg xmlns="http://www.w3.org/2000/svg"
                                                                                    class="w-5 h-5 mr-1" fill="none"
                                                                                    viewBox="0 0 24 24"
                                                                                    stroke="currentColor">
                                                                                    <path stroke-linecap="round"
                                                                                        stroke-linejoin="round"
                                                                                        stroke-width="2"
                                                                                        d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                                                                                </svg>
                                                                                <p>Active</p>
                                                                            </div>
                                                                        </td>
                                                                        <td
                                                                            class="px-6 py-4 whitespace-no-wrap text-sm leading-5">
                                                                            <div class="flex space-x-4">
                                                                                <a href="#" class="text-blue-500 hover:text-blue-600">
                                                                                <svg xmlns="http://www.w3.org/2000/svg"
                                                                                    class="w-5 h-5 mr-1"
                                                                                    fill="none" viewBox="0 0 24 24"
                                                                                    stroke="currentColor">
                                                                                    <path stroke-linecap="round"
                                                                                        stroke-linejoin="round"
                                                                                        stroke-width="2"
                                                                                        d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                                                                                </svg>
                                                                                <p>Edit</p>
                                                                                </a>
                                                                                <a href="#" class="text-red-500 hover:text-red-600">
                                                                                <svg xmlns="http://www.w3.org/2000/svg"
                                                                                    class="w-5 h-5 mr-1 ml-3"
                                                                                    fill="none" viewBox="0 0 24 24"
                                                                                    stroke="currentColor">
                                                                                    <path stroke-linecap="round"
                                                                                        stroke-linejoin="round"
                                                                                        stroke-width="2"
                                                                                        d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                                                                                </svg>
                                                                                <p>Delete</p>
                                                                                </a>
                                                                            </div>
                                                                        </td>
                                                                    </tr>
                                                                </tbody>
                                                            </table>
                                                        </div>
                                                    </div>
                                                </div>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </main>
        </div>
    </div>
    <script src="https://cdn.jsdelivr.net/npm/apexcharts"></script>
    <script>
        function data() {
          
            return {
               
                isSideMenuOpen: false,
                toggleSideMenu() {
                    this.isSideMenuOpen = !this.isSideMenuOpen
                },
                closeSideMenu() {
                    this.isSideMenuOpen = false
                },
                isNotificationsMenuOpen: false,
                toggleNotificationsMenu() {
                    this.isNotificationsMenuOpen = !this.isNotificationsMenuOpen
                },
                closeNotificationsMenu() {
                    this.isNotificationsMenuOpen = false
                },
                isProfileMenuOpen: false,
                toggleProfileMenu() {
                    this.isProfileMenuOpen = !this.isProfileMenuOpen
                },
                closeProfileMenu() {
                    this.isProfileMenuOpen = false
                },
                isPagesMenuOpen: false,
                togglePagesMenu() {
                    this.isPagesMenuOpen = !this.isPagesMenuOpen
                },
               
            }
        }
    </script>
    <script>
        var chart = document.querySelector('#chartline')
        var options = {
            series: [{
                name: 'TEAM A',
                type: 'area',
                data: [44, 55, 31, 47, 31, 43, 26, 41, 31, 47, 33]
            }, {
                name: 'TEAM B',
                type: 'line',
                data: [55, 69, 45, 61, 43, 54, 37, 52, 44, 61, 43]
            }],
            chart: {
                height: 350,
                type: 'line',
                zoom: {
                    enabled: false
                }
            },
            stroke: {
                curve: 'smooth'
            },
            fill: {
                type: 'solid',
                opacity: [0.35, 1],
            },
            labels: ['Dec 01', 'Dec 02', 'Dec 03', 'Dec 04', 'Dec 05', 'Dec 06', 'Dec 07', 'Dec 08', 'Dec 09 ',
                'Dec 10', 'Dec 11'
            ],
            markers: {
                size: 0
            },
            yaxis: [{
                    title: {
                        text: 'Series A',
                    },
                },
                {
                    opposite: true,
                    title: {
                        text: 'Series B',
                    },
                },
            ],
            tooltip: {
                shared: true,
                intersect: false,
                y: {
                    formatter: function(y) {
                        if (typeof y !== "undefined") {
                            return y.toFixed(0) + " points";
                        }
                        return y;
                    }
                }
            }
        };
        var chart = new ApexCharts(chart, options);
        chart.render();
    </script>
    <script>
        var chart = document.querySelector('#chartpie')
        var options = {
            series: [44, 55, 67, 83],
            chart: {
                height: 350,
                type: 'radialBar',
            },
            plotOptions: {
                radialBar: {
                    dataLabels: {
                        name: {
                            fontSize: '22px',
                        },
                        value: {
                            fontSize: '16px',
                        },
                        total: {
                            show: true,
                            label: 'Total',
                            formatter: function(w) {
                                // By default this function returns the average of all series. The below is just an example to show the use of custom formatter function
                                return 249
                            }
                        }
                    }
                }
            },
            labels: ['Apples', 'Oranges', 'Bananas', 'Berries'],
        };
        var chart = new ApexCharts(chart, options);
        chart.render();
    </script>
</body>

</html>
'''

HTML_TEMPLATES = {
    'layout1': '''
      <div class="flex h-screen bg-gray-800 " :class="{ 'overflow-hidden': isSideMenuOpen }">
        <main class="">
            <div class="grid mb-4 pb-10 px-8 mx-4 rounded-3xl bg-gray-100 border-4 border-green-400">
              {% for child in children %}
                  {{ child | safe }}
              {% endfor %}
            </div>
          </main>
      </div>
    ''',
    'layout': '''
        <div class="drawer">
          <input id="my-drawer-3" type="checkbox" class="drawer-toggle" />
          <div class="drawer-content flex flex-col">
            <!-- Navbar -->
            <div class="navbar bg-base-300 w-full">
              <div class="flex-none lg:hidden">
                <label for="my-drawer-3" aria-label="open sidebar" class="btn btn-square btn-ghost">
                  <svg
                    xmlns="http://www.w3.org/2000/svg"
                    fill="none"
                    viewBox="0 0 24 24"
                    class="inline-block h-6 w-6 stroke-current">
                    <path
                      stroke-linecap="round"
                      stroke-linejoin="round"
                      stroke-width="2"
                      d="M4 6h16M4 12h16M4 18h16"></path>
                  </svg>
                </label>
              </div>
              <div class="mx-2 flex-1 px-2">Navbar Title</div>
              <div class="hidden flex-none lg:block">
                <ul class="menu menu-horizontal">
                  <!-- Navbar menu content here -->
                  <li><a>Navbar Item 1</a></li>
                  <li><a>Navbar Item 2</a></li>
                </ul>
              </div>
            </div>
            <!-- Page content here -->
            <div class="grid mb-4 pb-10 px-8 mx-4 rounded-3xl bg-gray-100 border-4 border-green-400">
              {% for child in children %}
                  {{ child | safe }}
              {% endfor %}
            </div>
          </div>
          <div class="drawer-side">
            <label for="my-drawer-3" aria-label="close sidebar" class="drawer-overlay"></label>
            <ul class="menu bg-base-200 min-h-full w-80 p-4">
              <!-- Sidebar content here -->
              <li><a>Sidebar Item 1</a></li>
              <li><a>Sidebar Item 2</a></li>
            </ul>
          </div>
        </div>
    ''',
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
        <div class="grid 
            grid-cols-{{ attributes.columns.value if attributes.columns and attributes.columns and attributes.columns.value else '2' }} 
            {{ attributes.class.value if attributes and attributes.class and attributes.class.value }}">
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
                          <button hx-get="/edit?table_name={{ configs.table_name }}&id={{ row[data.primary_key] }}" hx-target="modal-content"
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
    'modal_form1': '''
         <dialog id="{{ attributes.id.value }}" class="modal">
            <div method="dialog" class="modal-box">
                <!-- <div id="modal-content" class="modal-content"> -->
                <!-- Form content will be loaded here -->
                <!-- </div> -->
            </div>
         </div>
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
          - type: grid
            children:
              - $ref: button
              - $ref: button
              - $ref: button
              - $ref: table_list1
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
  components:
    - type: layout
      children:
        - type: grid
          children:
            - $ref: button
            - $ref: button
            - $ref: button
        - $ref: main_data_table
        #- $ref: modal_message
        - $ref: modal_form
        
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
