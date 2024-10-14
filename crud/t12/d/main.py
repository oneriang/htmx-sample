import uvicorn
import time
from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from typing import List, Dict
from datetime import datetime

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}

    async def connect(self, websocket: WebSocket, username: str):
        await websocket.accept()
        self.active_connections[username] = websocket
        await self.broadcast(f"{username} has joined the chat")

    def disconnect(self, username: str):
        del self.active_connections[username]

    async def broadcast(self, message: str, sender: str = "System"):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        for connection in self.active_connections.values():
            await connection.send_text(f'''
            <div hx-swap-oob="beforeend:#chat-messages">
                <div class="chat {'chat-start' if sender == 'System' else 'chat-end'}">
                    <div class="chat-header">
                        {sender}
                        <time class="text-xs opacity-50">{timestamp}</time>
                    </div>
                    <div class="chat-bubble {'chat-bubble-primary' if sender != 'System' else ''}">{message}</div>
                </div>
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
        await manager.broadcast(f"{username} has left the chat")   

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