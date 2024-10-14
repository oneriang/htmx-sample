import uvicorn
import time
from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from typing import List, Dict

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}

    async def connect(self, websocket: WebSocket, username: str):
        await websocket.accept()
        self.active_connections[username] = websocket
        await self.broadcast(f"<p>{username} has joined the chat</p>")

    def disconnect(self, username: str):
        del self.active_connections[username]

    async def broadcast(self, message: str, sender: str = "System"):
        for connection in self.active_connections.values():
            await connection.send_text(f'''
            <div hx-swap-oob="beforeend:#chat-messages" class="message">
                <span>{time.time()}</span>
                <p><span class="username">{sender}:</span> {message}</p>
            </div>''')

manager = ConnectionManager()

@app.get("/")
async def get(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.websocket("/ws/{username}")
async def websocket_endpoint(websocket: WebSocket, username: str):
    await manager.connect(websocket, username)
    try:
        while True:
            data = await websocket.receive_json()
            await manager.broadcast(data['message'], username)
    except WebSocketDisconnect:
        manager.disconnect(username)
        await manager.broadcast(f"<p>{username} has left the chat</p>")   

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