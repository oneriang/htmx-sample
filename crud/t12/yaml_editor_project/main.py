'''
import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
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

@app.get("/files")
async def list_files():
    files = [f for f in os.listdir(YAML_DIR) if f.endswith('.yaml') or f.endswith('.yml')]
    return {"files": files}

@app.get("/file/{filename}")
async def read_file(filename: str):
    try:
        with open(os.path.join(YAML_DIR, filename), 'r') as file:
            content = file.read()
        return {"content": content}
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="File not found")

@app.post("/file/{filename}")
async def save_file(filename: str, request: Request):
    content = await request.body()
    content = content.decode()
    try:
        # 验证YAML格式
        yaml.safe_load(content)
        with open(os.path.join(YAML_DIR, filename), 'w') as file:
            file.write(content)
        return JSONResponse(content={"message": "File saved successfully"})
    except yaml.YAMLError as e:
        raise HTTPException(status_code=400, detail=f"Invalid YAML: {str(e)}")

@app.post("/new")
async def new_file(request: Request):
    data = await request.json()
    filename = data.get("filename")
    if not filename.endswith(('.yaml', '.yml')):
        filename += '.yaml'
    filepath = os.path.join(YAML_DIR, filename)
    if os.path.exists(filepath):
        raise HTTPException(status_code=400, detail="File already exists")
    with open(filepath, 'w') as file:
        file.write("")
    return {"message": "File created successfully"}
  '''  
  
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import yaml
import os
from pydantic import BaseModel

class FolderSettings(BaseModel):
    yaml_dir: str = "../"

settings = FolderSettings()

app = FastAPI()

# 挂载静态文件夹
app.mount("/static", StaticFiles(directory="static"), name="static")

# 设置模板
templates = Jinja2Templates(directory="templates")

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/files")
async def list_files():
    files = [f for f in os.listdir(settings.yaml_dir) if f.endswith('.yaml') or f.endswith('.yml')]
    return {"files": files}

@app.get("/file/{filename}")
async def read_file(filename: str):
    try:
        with open(os.path.join(settings.yaml_dir, filename), 'r') as file:
            content = file.read()
        return {"content": content}
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="File not found")

@app.post("/file/{filename}")
async def save_file(filename: str, request: Request):
    content = await request.body()
    content = content.decode()
    try:
        # 验证YAML格式
        yaml.safe_load(content)
        with open(os.path.join(settings.yaml_dir, filename), 'w') as file:
            file.write(content)
        return JSONResponse(content={"message": "File saved successfully"})
    except yaml.YAMLError as e:
        raise HTTPException(status_code=400, detail=f"Invalid YAML: {str(e)}")

@app.post("/new")
async def new_file(request: Request):
    data = await request.json()
    filename = data.get("filename")
    if not filename.endswith(('.yaml', '.yml')):
        filename += '.yaml'
    filepath = os.path.join(settings.yaml_dir, filename)
    if os.path.exists(filepath):
        raise HTTPException(status_code=400, detail="File already exists")
    with open(filepath, 'w') as file:
        file.write("")
    return {"message": "File created successfully"}

@app.post("/set_folder")
async def set_folder(request: Request):
    data = await request.json()
    new_folder = data.get("folder")
    if os.path.isdir(new_folder):
        settings.yaml_dir = new_folder
        return {"message": f"Folder set to: {new_folder}"}
    else:
        raise HTTPException(status_code=400, detail="Invalid folder path")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8081,
        reload=True,
        workers=2,
        log_level="debug",
        access_log=False,
        reload_dirs=["./"]
    )
