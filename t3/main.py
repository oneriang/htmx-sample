from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")

templates = Jinja2Templates(directory="templates")

# 模拟数据库数据
data = {
    "home": "This is the home page.",
    "about": "Here you can learn more about our company.",
    "contact": "Feel free to contact us if you have any questions."
}

@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    print(request.url)
    return templates.TemplateResponse("base.html", {"request": request, "content": data["home"]})

@app.get("/home", response_class=HTMLResponse)
def home(request: Request):
    print(request.url)
    print(request.url.query)
    print(request.query_params)
    query_params = request.query_params
    parameter_keys = query_params.keys()
    print(list(parameter_keys))
    return templates.TemplateResponse("home.html", {"request": request, "content": data["home"]})

@app.get("/about", response_class=HTMLResponse)
def about(request: Request):
    print(request.url)
    return templates.TemplateResponse("about.html", {"request": request, "content": data["about"]})

@app.get("/contact", response_class=HTMLResponse)
def contact(request: Request):
    print(request.url)
    return templates.TemplateResponse("contact.html", {"request": request, "content": data["contact"]})

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=9000)
