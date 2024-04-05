import os
import logging
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from starlette.responses import HTMLResponse
from starlette.middleware.cors import CORSMiddleware
import uuid
import json

app = FastAPI()

# CORS配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 日志配置
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("app.log"),
        logging.StreamHandler()
    ]
)

# 连接和会话管理
sessions = {}
peer_ids = {}

@app.websocket("/signaling")
async def signaling(websocket: WebSocket, x_peer_id: str = None):
    session_id = str(uuid.uuid4())
    sessions[session_id] = websocket
    peer_ids[session_id] = x_peer_id

    try:
        await websocket.accept()
        await websocket.send_text(json.dumps({"type": "connection_open"}))

        async for message in websocket.iter_text():
            data = json.loads(message)
            recipient_id = data.get("to")
            if recipient_id:
                for session, peer_id in peer_ids.items():
                    if peer_id == recipient_id:
                        await sessions[session].send_text(message)
            elif data.get("type") == "userlist":
                await websocket.send_text(json.dumps({"type": "userlist", "users": list(peer_ids.values())}))
    except WebSocketDisconnect:
        logging.info(f"WebSocket disconnection: {x_peer_id}")
        del sessions[session_id]
        del peer_ids[session_id]
        await broadcast_user_list()
    except Exception as e:
        logging.error(f"Error in signaling: {e}")

async def broadcast_user_list():
    user_list = list(peer_ids.values())
    for session in sessions.values():
        try:
            await session.send_text(json.dumps({"type": "userlist", "users": user_list}))
        except WebSocketDisconnect:
            logging.error("Error in broadcasting user list")

@app.get("/")
async def get():
    return HTMLResponse("""
        <!DOCTYPE html>
        <html>
        <head>
            <title>WebRTC Chat</title>
            <script src="https://unpkg.com/htmx.org@1.8.4"></script>
            <script src="https://unpkg.com/peerjs@1.4.7/dist/peerjs.min.js"></script>
        </head>
        <body>
            <h1>WebRTC Chat</h1>
            <div hx-target="this" hx-swap="innerHTML">
                <div id="user-list"></div>
                <div id="chat-container" style="display: none;">
                    <input type="text" id="recipient-id" placeholder="Enter Recipient's Peer ID">
                    <button hx-ws="send:/signaling" hx-trigger="click" hx-headers='{"X-Recipient-Id": document.getElementById("recipient-id").value, "X-Message": document.getElementById("chat-input").value}'>Send</button>
                    <input type="text" id="chat-input" placeholder="Type your message">
                    <ul id="messages"></ul>
                </div>
            </div>
            <script>
                var peer = new Peer();
                peer.on('open', function(id) {
                    document.getElementById('peer-id').value = id;
                    console.log('My peer ID is: ' + id);
                    hx.ajax('GET', '/signaling', {'X-Peer-Id': id, 'X-Message': 'userlist'});
                });
                peer.on('connection', function(conn) {
                    conn.on('open', function() {
                        conn.on('data', function(data) {
                            var li = document.createElement('li');
                            li.textContent = data;
                            document.getElementById('messages').appendChild(li);
                        });
                    });
                });
                document.addEventListener('htmx:wsopen', function(event) {
                    // 不需要再次请求用户列表
                });
                document.addEventListener('htmx:wsMessage', function(event) {
                    var data = JSON.parse(event.detail.data);
                    if (data.type === 'connection_open') {
                        console.log('WebSocket connection open');
                    } else if (data.type === 'userlist') {
                        updateUserList(data.users);
                    } else {
                        var conn = peer.connect(data.from);
                        conn.on('open', function() {
                            conn.send('Hello!');
                        });
                    }
                });
                function updateUserList(users) {
                    var userListDiv = document.getElementById('user-list');
                    userListDiv.innerHTML = '';
                    users.forEach(function(user) {
                        if (user !== document.getElementById('peer-id').value) {
                            var userDiv = document.createElement('div');
                            userDiv.textContent = user;
                            userDiv.onclick = function() {
                                document.getElementById('recipient-id').value = this.textContent;
                                document.getElementById('chat-container').style.display = 'block';
                            };
                            userListDiv.appendChild(userDiv);
                        }
                    });
                }
            </script>
        </body>
        </html>
    """)

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    logging.info(f"Starting server on port {port}")
    uvicorn.run(app, host="0.0.0.0", port=port)