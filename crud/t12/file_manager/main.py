import os
import uvicorn

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pathlib import Path

app = FastAPI()

# 设置静态文件目录
app.mount("/static", StaticFiles(directory="static"), name="static")
app.mount("/files", StaticFiles(directory="files"), name="files")

templates = Jinja2Templates(directory="templates")

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    files = os.listdir("files")
    return templates.TemplateResponse("index.html", {"request": request, "files": files})

@app.get("/preview/{filename}")
async def preview_file(request: Request, filename: str):
    file_path = Path(f"files/{filename}")
    if file_path.is_file():
        if file_path.suffix.lower() in ['.jpg', '.jpeg', '.png', '.gif']:
            return templates.TemplateResponse("preview.html", {"request": request, "filename": filename})
    return {"error": "File not found or not supported"}

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
