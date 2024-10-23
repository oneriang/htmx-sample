
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from database import execute_query

router = APIRouter()

@router.get("/tracks", response_class=HTMLResponse)
async def get_tracks(request: Request):
    query = f"SELECT * FROM Tracks LIMIT 10"
    tracks = execute_query(query)
    return templates.TemplateResponse("tracks.html", {"request": request, "tracks": tracks})
