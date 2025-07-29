from fastapi import WebSocket

class WebSocketManager:
    def __init__(self):
        self.active_connections = {}

    async def connect(self, session_id: str, websocket: WebSocket):
        await websocket.accept()
        self.active_connections[session_id] = websocket

    async def disconnect(self, session_id: str):
        self.active_connections.pop(session_id, None)

    async def send_to_overlay(self, session_id: str, message: dict):
        ws = self.active_connections.get(session_id)
        if ws:
            await ws.send_json(message)

manager = WebSocketManager()