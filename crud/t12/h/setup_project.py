import os
import shutil

def create_directory(path):
    os.makedirs(path, exist_ok=True)

def create_file(path, content):
    with open(path, 'w', encoding='utf-8') as file:
        file.write(content)

def setup_project():
    # 创建主目录结构
    create_directory('project')
    os.chdir('project')
    
    create_directory('api')
    create_directory('templates')
    create_directory('static/css')
    create_directory('static/js')

    # 创建主要的Python文件
    create_file('main.py', '''
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from database import execute_query

app = FastAPI()

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    stats = {
        "total_albums": execute_query("SELECT COUNT(*) FROM Album")[0][0],
        "total_artists": execute_query("SELECT COUNT(*) FROM Artist")[0][0],
        "total_tracks": execute_query("SELECT COUNT(*) FROM Track")[0][0],
        "total_customers": execute_query("SELECT COUNT(*) FROM Customer")[0][0],
        "total_employees": execute_query("SELECT COUNT(*) FROM Employee")[0][0],
        "total_invoices": execute_query("SELECT COUNT(*) FROM Invoice")[0][0],
    }
    return templates.TemplateResponse("index.html", {"request": request, "stats": stats})

@app.get("/api/stats", response_class=HTMLResponse)
async def get_stats(request: Request):
    stats = {
        "total_albums": execute_query("SELECT COUNT(*) FROM Album")[0][0],
        "total_artists": execute_query("SELECT COUNT(*) FROM Artist")[0][0],
        "total_tracks": execute_query("SELECT COUNT(*) FROM Track")[0][0],
        "total_customers": execute_query("SELECT COUNT(*) FROM Customer")[0][0],
        "total_employees": execute_query("SELECT COUNT(*) FROM Employee")[0][0],
        "total_invoices": execute_query("SELECT COUNT(*) FROM Invoice")[0][0],
    }
    return templates.TemplateResponse("stats_partial.html", {"request": request, "stats": stats})
''')

    create_file('database.py', '''
from sqlalchemy import create_engine, text

engine = create_engine("sqlite:///Chinook.db")

def execute_query(query, params=None):
    with engine.connect() as connection:
        result = connection.execute(text(query), params)
        return result.fetchall()
''')

    # 创建API模块文件
    api_modules = ['albums', 'artists', 'customers', 'employees', 'invoices', 'tracks']
    for module in api_modules:
        create_file(f'api/{module}.py', f'''
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from database import execute_query

router = APIRouter()

@router.get("/{module}", response_class=HTMLResponse)
async def get_{module}(request: Request):
    query = f"SELECT * FROM {module.capitalize()} LIMIT 10"
    {module} = execute_query(query)
    return templates.TemplateResponse("{module}.html", {{"request": request, "{module}": {module}}})
''')

    # 创建HTML模板
    create_file('templates/base.html', '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{% block title %}数字媒体商店管理系统{% endblock %}</title>
    <link rel="stylesheet" href="{{ url_for('static', path='/css/styles.css') }}">
    <script src="{{ url_for('static', path='/js/htmx.min.js') }}"></script>
</head>
<body>
    <header>
        <nav>
            <ul>
                <li><a href="/">首页</a></li>
                <li><a href="/albums">专辑</a></li>
                <li><a href="/artists">艺术家</a></li>
                <li><a href="/customers">客户</a></li>
                <li><a href="/employees">员工</a></li>
                <li><a href="/invoices">发票</a></li>
                <li><a href="/tracks">曲目</a></li>
            </ul>
        </nav>
    </header>

    <main>
        {% block content %}
        {% endblock %}
    </main>

    <footer>
        <p>&copy; 2024 数字媒体商店管理系统</p>
    </footer>
</body>
</html>
''')

    create_file('templates/index.html', '''
{% extends "base.html" %}

{% block title %}数字媒体商店管理系统 - 主页{% endblock %}

{% block content %}
<h1>数字媒体商店管理系统</h1>

<div id="stats-container" hx-trigger="load, every 30s" hx-get="/api/stats" hx-swap="innerHTML">
    {% include "stats_partial.html" %}
</div>

<section>
    <h2>快速操作</h2>
    <ul>
        <li><a href="/albums">管理专辑</a></li>
        <li><a href="/artists">管理艺术家</a></li>
        <li><a href="/customers">管理客户</a></li>
        <li><a href="/employees">管理员工</a></li>
        <li><a href="/invoices">查看发票</a></li>
        <li><a href="/tracks">浏览曲目</a></li>
    </ul>
</section>
{% endblock %}
''')

    create_file('templates/stats_partial.html', '''
<section id="system-stats">
    <h2>系统概览</h2>
    <ul>
        <li>总专辑数：{{ stats.total_albums }}</li>
        <li>总艺术家数：{{ stats.total_artists }}</li>
        <li>总曲目数：{{ stats.total_tracks }}</li>
        <li>总客户数：{{ stats.total_customers }}</li>
        <li>总员工数：{{ stats.total_employees }}</li>
        <li>总发票数：{{ stats.total_invoices }}</li>
    </ul>
</section>
''')

    # 为每个模块创建基本的HTML模板
    for module in api_modules:
        create_file(f'templates/{module}.html', f'''
{{% extends "base.html" %}}

{{% block title %}}{module.capitalize()} 管理{{% endblock %}}

{{% block content %}}
<h1>{module.capitalize()} 管理</h1>

<ul>
{{% for item in {module} %}}
    <li>{{{{ item }}}} </li>
{{% endfor %}}
</ul>
{{% endblock %}}
''')

    # 创建CSS文件
    create_file('static/css/styles.css', '''
body {
    font-family: Arial, sans-serif;
    line-height: 1.6;
    margin: 0;
    padding: 0;
    color: #333;
}

header {
    background-color: #4a4a4a;
    color: #fff;
    padding: 1rem 0;
}

nav ul {
    list-style-type: none;
    padding: 0;
    display: flex;
    justify-content: center;
}

nav ul li {
    margin: 0 10px;
}

nav ul li a {
    color: #fff;
    text-decoration: none;
}

main {
    padding: 20px;
    max-width: 1200px;
    margin: 0 auto;
}

h1, h2 {
    color: #2c3e50;
}

#system-stats ul {
    list-style-type: none;
    padding: 0;
}

#system-stats li {
    margin-bottom: 10px;
    font-size: 1.1em;
}

footer {
    background-color: #4a4a4a;
    color: #fff;
    text-align: center;
    padding: 1rem 0;
    position: fixed;
    bottom: 0;
    width: 100%;
}
''')

    # 下载 htmx.min.js
    htmx_url = "https://unpkg.com/htmx.org@1.9.10/dist/htmx.min.js"
    os.system(f"curl -o static/js/htmx.min.js {htmx_url}")

    print("项目结构和文件已成功创建。")

if __name__ == "__main__":
    setup_project()