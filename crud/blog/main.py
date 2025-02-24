# main.py
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi import APIRouter
from db import get_db
from models import models
from config import load_config
from datetime import datetime
from sqlalchemy import text

app = FastAPI()
templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")

# 创建路由
router = APIRouter()

# 动态注册路由
for route in load_config()['routes']:
    async def handler(request: Request, **params):
        action_name = route['handler']
        action = load_config()['actions'][action_name]
        model = models[action['model']]
        
        async with get_db() as db:
            if action['operation'] == 'read_all':
                query = model.select().order_by(text(action.get('order_by', '')))
                result = await db.execute(query)
                data = result.scalars().all()
                return templates.TemplateResponse(
                    route['template'],
                    {"request": request, "posts": data}
                )
                
            elif action['operation'] == 'create':
                form_data = await request.form()
                post_data = {k: form_data[k] for k in action['fields']}
                post_data['created_at'] = datetime.now()
                
                new_post = model(**post_data)
                db.add(new_post)
                await db.commit()
                return HTMLResponse(status_code=201)
                
            elif action['operation'] == 'read_one':
                post_id = params.get(action['id_param'])
                result = await db.execute(
                    model.select().where(model.id == post_id)
                )
                post = result.scalars().first()
                if not post:
                    raise HTTPException(status_code=404, detail="Post not found")
                return templates.TemplateResponse(
                    route['template'],
                    {"request": request, "post": post}
                )

    router.add_api_route(
        path=route['path'],
        endpoint=handler,
        methods=[route['method']],
        name=route['handler']
    )

app.include_router(router)

# main.py 末尾添加
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)