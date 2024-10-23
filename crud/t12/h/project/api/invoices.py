
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from database import execute_query

router = APIRouter()

@router.get("/invoices", response_class=HTMLResponse)
async def get_invoices(request: Request):
    query = f"SELECT * FROM Invoices LIMIT 10"
    invoices = execute_query(query)
    return templates.TemplateResponse("invoices.html", {"request": request, "invoices": invoices})
