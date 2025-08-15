from fastapi import APIRouter, WebSocket, WebSocketDisconnect
import asyncio
from collections import defaultdict
from typing import Optional, Dict, Set

from app.Chat_Manager import (
    pick_character, set_character, remove_character,
    reset_all_pools, reset_character_pool, update_character_voice_style,
    mute_character_tts, message_as_character,
)
from app.functions.ChanceGames import shoot_gun, flip_gun, hide_gun, start_crates_game, select_crate, reset_crates
from app.functions.poll_manager import start_poll, end_poll, hide_poll
from app.functions.Duel_poll_manager import start_duel_poll, end_duel_poll, hide_duel_poll

router = APIRouter()

# ------------------------------------------------------------------------------
# Shared registry for character control (supports multiple concurrent UIs)
# ------------------------------------------------------------------------------
# Track which websockets are controlling / watching which character
_conn_by_char: Dict[int, Set[WebSocket]] = defaultdict(set)

# Serialize operations per character to avoid race conditions
_locks_by_char: Dict[int, asyncio.Lock] = defaultdict(asyncio.Lock)


async def _broadcast_to_char(char: int, payload: dict):
    """
    Send a message to all clients currently connected for a given character.
    Removes dead sockets on send failure.
    """
    dead: list[WebSocket] = []
    for ws in list(_conn_by_char.get(char, ())):
        try:
            await ws.send_json(payload)
            print(f"[Broadcast] Sent to character {char}: {payload}")
        except Exception:
            print(f"[Broadcast] Failed to send to character {char}, removing dead socket.")
            dead.append(ws)
    for ws in dead:
        print(f"[Broadcast] Removing dead socket for character {char}.")
        _conn_by_char[char].discard(ws)


# ------------------------------------------------------------------------------
# Existing endpoints (kept for compatibility) with safer exception logging
# ------------------------------------------------------------------------------

@router.websocket("/ws/pick_character")
async def ws_pick_character(websocket: WebSocket):
    await websocket.accept()
    last_char: Optional[int] = None
    try:
        while True:
            data = await websocket.receive_json()
            last_char = data.get("character_number")
            platform = data.get("platform")
            username = await pick_character(last_char, platform)
            await websocket.send_json({"character": last_char, "username": username, "platform": platform})
    except WebSocketDisconnect as e:
        print(f"WebSocket disconnected while picking character {last_char}. Error: {e}")


@router.websocket("/ws/set_character")
async def ws_set_character(websocket: WebSocket):
    await websocket.accept()
    last_char: Optional[int] = None
    try:
        while True:
            data = await websocket.receive_json()
            last_char = data.get("character_number")
            username = data.get("username")
            platform = data.get("platform")
            await set_character(last_char, username, platform)
            await websocket.send_json({"character": last_char, "username": username, "platform": platform})
    except WebSocketDisconnect as e:
        print(f"WebSocket disconnected while setting character {last_char}. Error: {e}")


@router.websocket("/ws/mute_tts")
async def ws_mute_tts(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_json()
            mute = data.get("mute")
            print(f"Received mute command: {mute}")
            status = await mute_character_tts(mute)
            await websocket.send_json({"status": status})
    except WebSocketDisconnect as e:
        print(f"WebSocket disconnected while muting TTS. Error: {e}")


@router.websocket("/ws/shoot_gun")
async def ws_shoot_gun(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_json()
            gun_action = data.get("command")
            print(f"Received gun action: {gun_action}")
            if gun_action == "shoot":
                result = await shoot_gun()
                await websocket.send_json({"status": result})
            elif gun_action == "flip":
                result = await flip_gun()
                await websocket.send_json({"status": result})
            elif gun_action == "hide":
                result = await hide_gun()
                await websocket.send_json({"status": result})
            else:
                await websocket.send_json({"status": "Invalid action"})
    except WebSocketDisconnect as e:
        print(f"WebSocket disconnected while shooting gun. Error: {e}")


@router.websocket("/ws/reset_characters")
async def ws_reset_characters(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            await websocket.receive_text()  # any message triggers reset
            for number in range(1, 11):  # MAX_CHARACTERS is 10
                await remove_character(number)
            await websocket.send_json({"status": "characters_reset"})
    except WebSocketDisconnect as e:
        print(f"WebSocket disconnected while resetting characters. Error: {e}")


@router.websocket("/ws/reset_character")
async def ws_reset_character(websocket: WebSocket):
    await websocket.accept()
    last_char: Optional[int] = None
    try:
        while True:
            data = await websocket.receive_json()
            last_char = data.get("character_number")
            await remove_character(last_char)
            await reset_character_pool(last_char)
            await websocket.send_json({"status": f"character_{last_char}_reset"})
    except WebSocketDisconnect as e:
        print(f"WebSocket disconnected while resetting character {last_char}. Error:  {e}")


@router.websocket("/ws/set_voice_style")
async def ws_set_voice_style(websocket: WebSocket):
    """
    WebSocket endpoint to set the voice style for a character.
    Expects: { "character_number": int, "voice_style": "af_bella" }
    """
    await websocket.accept()
    last_char: Optional[int] = None
    try:
        while True:
            data = await websocket.receive_json()
            last_char = data.get("character_number")
            voice_style = data.get("voice_style")
            if last_char and voice_style:
                await update_character_voice_style(last_char, voice_style)
                await websocket.send_json({"status": "ok", "character_number": last_char, "voice_style": voice_style})
            else:
                await websocket.send_json({"status": "error", "detail": "Invalid character_number or voice_style"})
    except WebSocketDisconnect as e:
        print(f"WebSocket disconnected while setting voice style for character {last_char}. Error: {e}")


@router.websocket("/ws/message_as_character")
async def ws_message_as_character(websocket: WebSocket):
    """
    WebSocket endpoint to send a message as a character.
    Expects: { "character_number": int, "alias": str, "message": str }
    """
    await websocket.accept()
    last_char: Optional[int] = None
    try:
        while True:
            data = await websocket.receive_json()
            last_char = data.get("character_number")
            alias = data.get("alias")
            message = data.get("message")
            if last_char and alias and message:
                # If message_as_character is async in your codebase, add 'await' here.
                message_as_character(last_char, message, alias)
                await websocket.send_json({"status": "ok", "character_number": last_char, "alias": alias, "message": message})
            else:
                print(f"Invalid details received: {data}")
                await websocket.send_json({"status": "error", "detail": "Invalid details"})
    except WebSocketDisconnect as e:
        print(f"WebSocket disconnected while sending message as character {last_char}. Error: {e}")


@router.websocket("/ws/control_poll")
async def ws_control_poll(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_json()
            poll = data.get("poll")
            print(f"Received poll state: {poll}")
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

@router.websocket("/ws/control_duel_poll")
async def ws_control_duel_poll(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_json()
            poll = data.get("poll")
            print(f"Received duel poll state: {poll}")
            if poll == "start":
                status = await start_duel_poll()
            elif poll == "end":
                status = await end_duel_poll()
            elif poll == "hide":
                status = await hide_duel_poll()
            else:
                status = "Invalid poll command"
            await websocket.send_json({"status": status})
    except WebSocketDisconnect as e:
        print(f"WebSocket disconnected while controlling duel poll. Error: {e}")


# ------------------------------------------------------------------------------
# Crates game WebSocket (already structured for persistent use)
# ------------------------------------------------------------------------------

@router.websocket("/ws/crates")
async def ws_crates(websocket: WebSocket):
    """
    WebSocket control channel for the Crates game.

    Client -> Server messages:
      { "type": "crates:start", "sceneName"?: string }
      { "type": "crates:select", "crate": number, "sceneName"?: string }
      { "type": "crates:reset", "sceneName"?: string }
      { "type": "crates:status:get" }

    Server -> Client messages:
      { "type": "ok", "message"?: string }
      { "type": "error", "message": string }
      { "type": "crates:status", "active": bool, "message"?: string, "opened"?: number[] }
      { "type": "crates:result", "message": string, "active"?: bool, "opened"?: number[] }
    """
    await websocket.accept()
    last_active: Optional[bool] = None

    try:
        while True:
            data = await websocket.receive_json()
            msg_type = data.get("type")
            scene_name: Optional[str] = data.get("sceneName")

            if msg_type == "crates:start":
                try:
                    msg = await start_crates_game(scene_name=scene_name) if scene_name else await start_crates_game()
                    last_active = True
                    await websocket.send_json({
                        "type": "crates:status",
                        "active": True,
                        "message": msg,
                    })
                except Exception as e:
                    await websocket.send_json({"type": "error", "message": f"Failed to start: {e}"})

            elif msg_type == "crates:select":
                crate = data.get("crate")
                if not isinstance(crate, int) or not (1 <= crate <= 12):
                    await websocket.send_json({"type": "error", "message": "Invalid crate number. Use 1–12."})
                    continue
                try:
                    result_msg = await select_crate(crate_number=crate, scene_name=scene_name) if scene_name else await select_crate(crate_number=crate)
                    is_over = "game over" in result_msg.lower()
                    if is_over:
                        last_active = False
                    elif last_active is None:
                        last_active = True
                    await websocket.send_json({
                        "type": "crates:result",
                        "message": result_msg,
                        "active": False if is_over else True,
                    })
                except Exception as e:
                    await websocket.send_json({"type": "error", "message": f"Selection failed: {e}"})

            elif msg_type == "crates:reset":
                try:
                    msg = await reset_crates(scene_name=scene_name) if scene_name else await reset_crates()
                    last_active = False
                    await websocket.send_json({
                        "type": "crates:status",
                        "active": False,
                        "message": msg,
                    })
                except Exception as e:
                    await websocket.send_json({"type": "error", "message": f"Failed to reset: {e}"})

            elif msg_type == "crates:status:get":
                await websocket.send_json({
                    "type": "crates:status",
                    "active": bool(last_active) if last_active is not None else False,
                    "message": "Status report",
                })

            else:
                await websocket.send_json({"type": "error", "message": f"Unknown command: {msg_type}"})
    except WebSocketDisconnect as e:
        print(f"Crates WS disconnected: {e}")


# ------------------------------------------------------------------------------
# NEW: Single persistent WebSocket for all character controls with
#      per-character locking and broadcast to all viewers of that character.
# ------------------------------------------------------------------------------

@router.websocket("/ws/character_control")
async def ws_character_control(websocket: WebSocket):
    """
    Persistent WebSocket for character control.

    Connect with a pinned character:
      ws://host/ws/character_control?character=3

    Client -> Server:
      { "type": "character:pick",    "platform"?: "twitch"|"tiktok"|"either" }
      { "type": "character:set",     "username": str, "platform"?: str }
      { "type": "character:reset" }
      { "type": "character:voice",   "voice_style": str }
      { "type": "character:message", "alias": str, "message": str }
      { "type": "character:status:get" }

    Server -> Client (broadcast to all viewers of the character):
      { "type": "character:picked", "character": int, "username": str, "platform"?: str }
      { "type": "ok", "status": "character_<n>_reset", "character": int }
      { "type": "ok", "context": "voice", "character": int, "voice_style": str }
      { "type": "ok", "context": "message", "character": int }
      { "type": "error", "message": str }   # sent only to the requester
    """
    await websocket.accept()

    # Require a character in the query to keep registry simple (one character per socket)
    default_character: Optional[int] = None
    q_char = websocket.query_params.get("character")
    if q_char is not None:
        try:
            default_character = int(q_char)
        except ValueError:
            default_character = None

    if default_character is None:
        await websocket.send_json({"type": "error", "message": "Supply ?character=<number> in the URL"})
        await websocket.close()
        return

    # Register this connection
    _conn_by_char[default_character].add(websocket)

    try:
        while True:
            data = await websocket.receive_json()
            msg_type = data.get("type")
            char = default_character  # enforce one-character-per-connection

            async def ok(payload: dict = {}):
                # broadcast OKs so all UIs sync (status, voice, message ack, reset)
                await _broadcast_to_char(char, {"type": "ok", **payload})

            async def err(message: str):
                # errors only to the requester
                await websocket.send_json({"type": "error", "message": message})

            lock = _locks_by_char[char]

            if msg_type == "character:pick":
                platform = data.get("platform", "either")
                async with lock:
                    try:
                        username = await pick_character(char, platform)
                        await _broadcast_to_char(char, {
                            "type": "character:picked",
                            "character": char,
                            "username": username,
                            "platform": platform,
                        })
                    except Exception as e:
                        await err(f"Pick failed: {e}")

            elif msg_type == "character:set":
                username = data.get("username")
                platform = data.get("platform", "either")
                if not username:
                    await err("username is required")
                    continue
                async with lock:
                    try:
                        await set_character(char, username, platform)
                        await _broadcast_to_char(char, {
                            "type": "character:picked",
                            "character": char,
                            "username": username,
                            "platform": platform,
                        })
                    except Exception as e:
                        await err(f"Set failed: {e}")

            elif msg_type == "character:reset":
                async with lock:
                    try:
                        await remove_character(char)
                        await reset_character_pool(char)
                        await ok({"status": f"character_{char}_reset", "character": char})
                    except Exception as e:
                        await err(f"Reset failed: {e}")

            elif msg_type == "character:voice":
                voice_style = data.get("voice_style")
                if not voice_style:
                    await err("voice_style is required")
                    continue
                async with lock:
                    try:
                        await update_character_voice_style(char, voice_style)
                        await ok({"context": "voice", "character": char, "voice_style": voice_style})
                    except Exception as e:
                        await err(f"Voice update failed: {e}")

            elif msg_type == "character:message":
                alias = data.get("alias")
                text = data.get("message")
                if not alias or not text:
                    await err("alias and message are required")
                    continue
                # Usually okay without the lock; keep for ordering if desired
                async with lock:
                    try:
                        message_as_character(char, text, alias)
                        await ok({"context": "message", "character": char})
                    except Exception as e:
                        await err(f"Message send failed: {e}")

            elif msg_type == "character:status:get":
                await ok({"context": "status", "character": char})

            else:
                await err(f"Unknown command: {msg_type}")

    except WebSocketDisconnect:
        pass
    finally:
        _conn_by_char[default_character].discard(websocket)
