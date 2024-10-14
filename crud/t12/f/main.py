import uvicorn
from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from typing import Dict
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
        await self.broadcast(content=f"{username} has joined the chat")
        await self.update_user_list()

    def disconnect(self, username: str):
        del self.active_connections[username]

    async def broadcast(self, content: str, sender: str = "System"):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        for username, connection in self.active_connections.items():
            message = f'''
                <div hx-swap-oob="beforeend:#chat-messages">
                    <div class="chat {'chat-start' if sender == 'System' or username != sender else 'chat-end'}">
                        <div class="chat-header">
                            {sender}
                            <time class="text-xs opacity-50">{timestamp}</time>
                        </div>
                        <div class="chat-bubble {'chat-bubble-primary' if sender != 'System' or username == sender else ''}">{content}</div>
                    </div>
                </div>
            '''
            await connection.send_text(message)

    async def send_private_message(self, sender: str, recipient: str, content: str):
        if recipient in self.active_connections:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            message = f'''
            <div hx-swap-oob="beforeend:#chat-messages">
                <div class="chat {'chat-end' if sender == recipient else 'chat-start'}">
                    <div class="chat-header">
                        {sender}
                        <time class="text-xs opacity-50">{timestamp}</time>
                    </div>
                    <div class="chat-bubble {'chat-bubble-primary' if sender != recipient else ''}">{content}</div>
                </div>
            </div>'''
            await self.active_connections[recipient].send_text(message)
            await self.active_connections[sender].send_text(message)

    async def update_user_list(self):
        user_list = list(self.active_connections.keys())
        message = '<div hx-swap-oob="innerHTML:#online-users">'
        for user in user_list:
            message += f'''
                <li class="cursor-pointer hover:text-primary" onclick="startPrivateChat('{user}')">
                    {user}
                </li>
            '''
        message += '</div>'
        print(self.active_connections)
        for username, connection in self.active_connections.items():
            print(username)
            await connection.send_text(message)

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
            print(data)
            if data["type"] == "chat_message":
                await manager.broadcast(content=data["content"], sender=username)
            elif data["type"] == "private_message":
                await manager.send_private_message(username, data["recipient"], data["content"])
    except WebSocketDisconnect:
        manager.disconnect(username)
        await manager.update_user_list()
        await manager.broadcast(f"{username} has left the chat")
        
if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
