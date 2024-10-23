import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from database import execute_query

from api import albums, artists, customers, employees, invoices, tracks

app = FastAPI()

# 包含各个模块的路由
app.include_router(albums.router)
app.include_router(artists.router)
app.include_router(customers.router)
app.include_router(employees.router)
app.include_router(invoices.router)
app.include_router(tracks.router)

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
