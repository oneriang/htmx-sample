
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from database import execute_query

router = APIRouter()

@router.get("/customers", response_class=HTMLResponse)
async def get_customers(request: Request):
    query = f"SELECT * FROM Customers LIMIT 10"
    customers = execute_query(query)
    return templates.TemplateResponse("customers.html", {"request": request, "customers": customers})
