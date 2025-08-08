from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.Chat_Manager import (
    pick_character, set_character, remove_character,
    reset_all_pools, reset_character_pool, update_character_voice_style, mute_character_tts, message_as_character,
)
from app.functions.poll_manager import start_poll, end_poll, hide_poll

router = APIRouter()

@router.websocket("/ws/pick_character")
async def ws_pick_character(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_json()
            character_number = data.get("character_number")
            platform = data.get("platform")
            username = pick_character(character_number, platform)
            await websocket.send_json({"character": character_number, "username": username, "platform": platform})
    except WebSocketDisconnect as e:
        print(f"WebSocket disconnected while picking character {character_number}. Error: {e}")
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
            set_character(character_number, username, platform)
            await websocket.send_json({"character": character_number, "username": username, "platform": platform})
    except WebSocketDisconnect as e:
        print(f"WebSocket disconnected while setting character {character_number}. Error: {e}")
        pass

@router.websocket("/ws/mute_tts")
async def ws_mute_tts(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_json()
            mute = data.get("mute")
            print(f"Received mute command: {mute}")
            print(f"Muting TTS: {mute}")
            status = mute_character_tts(mute)
            await websocket.send_json({"status": status})
    except WebSocketDisconnect as e:
        print(f"WebSocket disconnected while muting TTS. Error: {e}")
        pass



@router.websocket("/ws/reset_characters")
async def ws_reset_characters(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            await websocket.receive_text()  # Just wait for any message to trigger reset
            for number in range(1, 11):  # MAX_CHARACTERS is 10
                remove_character(number)
            await websocket.send_json({"status": "characters_reset"})
    except WebSocketDisconnect as e:
        print(f"WebSocket disconnected while resetting characters. Error: {e}")
        pass

@router.websocket("/ws/reset_character")
async def ws_reset_character(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_json()
            character_number = data.get("character_number")
            remove_character(character_number)
            reset_character_pool(character_number)
            await websocket.send_json({"status": f"character_{character_number}_reset"})
    except WebSocketDisconnect as e:
        print(f"WebSocket disconnected while resetting character {character_number}. Error:  {e}")
        pass

@router.websocket("/ws/set_voice_style")
async def ws_set_voice_style(websocket: WebSocket):
    """
    WebSocket endpoint to set the voice style for a character.
    Expects: { "character_number": int, "voice_style": "af_bella" }
    """
    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_json()
            character_number = data.get("character_number")
            voice_style = data.get("voice_style")
            if character_number and voice_style:
                update_character_voice_style(character_number, voice_style)
                await websocket.send_json({"status": "ok", "character_number": character_number, "voice_style": voice_style})
            else:
                await websocket.send_json({"status": "error", "detail": "Invalid character_number or voice_style"})
    except WebSocketDisconnect as e:
        print(f"WebSocket disconnected while setting voice style for character {character_number}. Error: {e}")
        pass

@router.websocket("/ws/message_as_character")
async def ws_message_as_character(websocket: WebSocket):
    """
    WebSocket endpoint to set the voice style for a character.
    Expects: { "character_number": int, "voice_style": "af_bella" }
    """
    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_json()
            character_number = data.get("character_number")
            alias = data.get("alias")
            message = data.get("message")
            if character_number and alias and message:
                message_as_character(character_number, message, alias)
                await websocket.send_json({"status": "ok", "character_number": character_number, "alias": alias, "message": message})
            else:
                print(f"Invalid details received: {data}")
                await websocket.send_json({"status": "error", "detail": "Invalid details"})
    except WebSocketDisconnect as e:
        print(f"WebSocket disconnected while sending message as character {character_number}. Error: {e}")
        pass

@router.websocket("/ws/control_poll")
async def ws_control_poll(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_json()
            poll = data.get("poll")
            print(f"Received poll state: {poll}")
            print(f"Setting poll state: {poll}")
            if poll == "start":
                status = await start_poll()
            elif poll == "end":
                status = await end_poll()
            elif poll == "hide":
                status = await hide_poll()
            else:
                status = "Invalid poll command"
            await websocket.send_json({"status": status})
    except WebSocketDisconnect as e:
        print(f"WebSocket disconnected while controlling poll. Error: {e}")
        pass