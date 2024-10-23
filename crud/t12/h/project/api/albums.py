'''
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from database import execute_query

router = APIRouter()

@router.get("/albums", response_class=HTMLResponse)
async def get_albums(request: Request):
    query = f"SELECT * FROM Albums LIMIT 10"
    albums = execute_query(query)
    return templates.TemplateResponse("albums.html", {"request": request, "albums": albums})
'''

# api/albums.py

from fastapi import APIRouter, Request, Form, HTTPException
from fastapi.responses import HTMLResponse
from database import execute_query
from fastapi.templating import Jinja2Templates

router = APIRouter()
templates = Jinja2Templates(directory="templates")

@router.get("/albums", response_class=HTMLResponse)
async def get_albums(request: Request):
    query = "SELECT Album.AlbumId, Album.Title, Artist.Name as ArtistName FROM Album JOIN Artist ON Album.ArtistId = Artist.ArtistId"
    albums = execute_query(query)
    return templates.TemplateResponse("albums.html", {"request": request, "albums": albums})

@router.get("/albums/new", response_class=HTMLResponse)
async def new_album_form(request: Request):
    artists_query = "SELECT ArtistId, Name FROM Artist"
    artists = execute_query(artists_query)
    return templates.TemplateResponse("album_form.html", {"request": request, "artists": artists})

@router.post("/albums/new", response_class=HTMLResponse)
async def create_album(request: Request, title: str = Form(...), artist_id: int = Form(...)):
    query = "INSERT INTO Album (Title, ArtistId) VALUES (?, ?)"
    execute_query(query, (title, artist_id))
    return await get_albums(request)

@router.get("/albums/{album_id}/edit", response_class=HTMLResponse)
async def edit_album_form(request: Request, album_id: int):
    album_query = "SELECT AlbumId, Title, ArtistId FROM Album WHERE AlbumId = ?"
    album = execute_query(album_query, (album_id,))[0]
    artists_query = "SELECT ArtistId, Name FROM Artist"
    artists = execute_query(artists_query)
    return templates.TemplateResponse("album_form.html", {"request": request, "album": album, "artists": artists})

@router.post("/albums/{album_id}/edit", response_class=HTMLResponse)
async def update_album(request: Request, album_id: int, title: str = Form(...), artist_id: int = Form(...)):
    query = "UPDATE Album SET Title = ?, ArtistId = ? WHERE AlbumId = ?"
    execute_query(query, (title, artist_id, album_id))
    return await get_albums(request)

@router.delete("/albums/{album_id}", response_class=HTMLResponse)
async def delete_album(request: Request, album_id: int):
    query = "DELETE FROM Album WHERE AlbumId = ?"
    execute_query(query, (album_id,))
    return await get_albums(request)