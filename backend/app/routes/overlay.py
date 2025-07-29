from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.websocket_manager import manager

router = APIRouter()

@router.websocket("/ws/overlay/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    await manager.connect(session_id, websocket)
    try:
        while True:
            data = await websocket.receive_text()
    except WebSocketDisconnect:
        await manager.disconnect(session_id)

@router.post("/control/{session_id}/{game_name}")
async def trigger_game(session_id: str, game_name: str):
    await manager.send_to_overlay(session_id, {"action": "start_game", "game": game_name})
    return {"status": "sent"}