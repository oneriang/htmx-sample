
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from database import execute_query

router = APIRouter()

@router.get("/artists", response_class=HTMLResponse)
async def get_artists(request: Request):
    query = f"SELECT * FROM Artists LIMIT 10"
    artists = execute_query(query)
    return templates.TemplateResponse("artists.html", {"request": request, "artists": artists})
