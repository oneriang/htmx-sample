#!/bin/bash

# 创建主项目目录
mkdir -p yaml_editor_project
cd yaml_editor_project

# 创建必要的子目录
mkdir -p templates static yaml_files

# 创建 main.py 文件
cat << EOF > main.py
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import yaml
import os

app = FastAPI()

# 挂载静态文件夹
app.mount("/static", StaticFiles(directory="static"), name="static")

# 设置模板
templates = Jinja2Templates(directory="templates")

# YAML文件存储路径
YAML_DIR = "yaml_files"

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

# 其他路由和功能...

EOF

# 创建 index.html 模板文件
cat << EOF > templates/index.html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>YAML Editor</title>
    <script src="https://unpkg.com/htmx.org@1.9.10"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/ace/1.32.6/ace.js"></script>
    <style>
        #editor { 
            height: 400px;
            width: 100%;
        }
    </style>
</head>
<body>
    <h1>YAML Editor</h1>
    <!-- 编辑器内容 -->
</body>
</html>
EOF

# 创建一个示例YAML文件
echo "example: true" > yaml_files/example.yaml

echo "项目结构已创建完成。"