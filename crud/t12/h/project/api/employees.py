
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from database import execute_query

router = APIRouter()

@router.get("/employees", response_class=HTMLResponse)
async def get_employees(request: Request):
    query = f"SELECT * FROM Employees LIMIT 10"
    employees = execute_query(query)
    return templates.TemplateResponse("employees.html", {"request": request, "employees": employees})
