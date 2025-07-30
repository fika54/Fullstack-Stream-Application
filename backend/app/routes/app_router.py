from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.Chat_Manager import (
    pick_character_1, pick_character_2,
    set_character_1, set_character_2,
    remove_character_1, remove_character_2,
    reset_all_pools, reset_character_1_pool, reset_character_2_pool,
    update_character_voice_style
)

router = APIRouter()

@router.websocket("/ws/pick_character")
async def ws_pick_character(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_json()
            character_number = data.get("character_number")
            platform = data.get("platform")
            if character_number == 1:
                username = pick_character_1(platform)
                await websocket.send_json({"character": 1, "username": username, "platform": platform})
            elif character_number == 2:
                username = pick_character_2(platform)
                await websocket.send_json({"character": 2, "username": username, "platform": platform})
    except WebSocketDisconnect:
        pass

@router.websocket("/ws/set_character")
async def ws_set_character(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_json()
            character_number = data.get("character_number")
            username = data.get("username")
            platform = data.get("platform")
            if character_number == 1:
                set_character_1(username, platform)
                await websocket.send_json({"character": 1, "username": username, "platform": platform})
            elif character_number == 2:
                set_character_2(username, platform)
                await websocket.send_json({"character": 2, "username": username, "platform": platform})
    except WebSocketDisconnect:
        pass

@router.websocket("/ws/reset_characters")
async def ws_reset_characters(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            await websocket.receive_text()  # Just wait for any message to trigger reset
            remove_character_1()
            remove_character_2()
            await websocket.send_json({"status": "characters_reset"})
    except WebSocketDisconnect:
        pass

@router.websocket("/ws/reset_character")
async def ws_reset_character(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_json()
            character_number = data.get("character_number")
            if character_number == 1:
                remove_character_1()
                reset_character_1_pool()
                await websocket.send_json({"status": "character_1_reset"})
            elif character_number == 2:
                remove_character_2()
                reset_character_2_pool()
                await websocket.send_json({"status": "character_2_reset"})
    except WebSocketDisconnect:
        pass

@router.websocket("/ws/set_voice_style")
async def ws_set_voice_style(websocket: WebSocket):
    """
    WebSocket endpoint to set the voice style for a character.
    Expects: { "character_number": 1 or 2, "voice_style": "af_bella" }
    """
    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_json()
            character_number = data.get("character_number")
            voice_style = data.get("voice_style")
            if character_number in [1, 2] and voice_style:
                update_character_voice_style(character_number, voice_style)
                await websocket.send_json({"status": "ok", "character_number": character_number, "voice_style": voice_style})
            else:
                await websocket.send_json({"status": "error", "detail": "Invalid character_number or voice_style"})
    except WebSocketDisconnect:
        pass