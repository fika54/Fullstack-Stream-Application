# duel_poll.py
import asyncio
import functools
from typing import Optional, Dict, Tuple

from app.functions.obs_websocket import OBSWebsocketsManager
from app.functions.audio_player import AudioManager

# -----------------------------
# Configuration (edit names!)
# -----------------------------
SCENE_NAME = "Vote duel"                 # Scene that contains the circles + timer
BLUE_TEMPLATE = "Blue Circle {i}"        # e.g., "Blue Circle 1" .. "Blue Circle 8"
RED_TEMPLATE = "Red Circle {i}"          # e.g., "Red Circle 1" .. "Red Circle 8"
TIMER_SOURCE_NAME = "Timer"              # Text source that shows MM:SS

DEFAULT_TOTAL_CIRCLES = 8                # How many circles per side to show
END_THRESHOLD = 0.70                     # 80% auto-end threshold
SFX_PROGRESS_PATH = "app/Sound effects/duel_vote.mp3"
SFX_WIN_PATH = "app/Sound effects/Duel_win.mp3"

OBS = OBSWebsocketsManager()
AUDIO = AudioManager()

# -----------------------------------------------------------------------------
# Internal state
# -----------------------------------------------------------------------------
_lock = asyncio.Lock()
_votes = {"1": 0, "2": 0}               # real votes
_active: bool = False
_total_circles: int = DEFAULT_TOTAL_CIRCLES
_timer_task: Optional[asyncio.Task] = None
_time_left_s: int = 0

# last rendered counts (to detect visual changes)
_last_blue_on: int = 0
_last_red_on: int = 0

# Cache for OBS v5 scene item ids
_scene_item_id_cache: Dict[Tuple[str, str], int] = {}

# -----------------------------------------------------------------------------
# OBS helpers (visibility + text)
# -----------------------------------------------------------------------------
async def _get_scene_item_id_async(scene_name: str, source_name: str) -> int:
    """
    Resolve and cache OBS v5 sceneItemId for (scene, source).
    Tries common wrapper methods:
      - get_scene_item_id(scene_name, source_name) -> int
      - get_scene_item_list(scene_name) -> list[{ 'sourceName','sceneItemId' },...]
    """
    key = (scene_name, source_name)
    if key in _scene_item_id_cache:
        return _scene_item_id_cache[key]

    loop = asyncio.get_running_loop()

    # Direct helper
    if hasattr(OBS, "get_scene_item_id"):
        item_id = await loop.run_in_executor(
            None, functools.partial(OBS.get_scene_item_id, scene_name, source_name)
        )
        _scene_item_id_cache[key] = int(item_id)
        return int(item_id)

    # Fallback: list items and find match
    for cand in ("get_scene_item_list", "list_scene_items", "get_scene_items"):
        if hasattr(OBS, cand):
            items = await loop.run_in_executor(
                None, functools.partial(getattr(OBS, cand), scene_name)
            )
            for it in items or []:
                name = it.get("sourceName") or it.get("name")
                sid = it.get("sceneItemId") or it.get("id")
                if isinstance(name, str) and name == source_name and isinstance(sid, int):
                    _scene_item_id_cache[key] = sid
                    return sid
            break

    raise RuntimeError(
        f"Could not resolve sceneItemId for '{source_name}' in scene '{scene_name}'. "
        "Check source names and that your OBS wrapper can list scene items."
    )

async def _set_item_visibility_async(scene_name: str, source_name: str, visible: bool):
    """
    Toggle visibility for a scene item.

    >>> THIS is the exact spot where we set OBS source visibility. <<<

    - For OBS v5 wrappers, we resolve the sceneItemId and call:
        set_scene_item_enabled(scene, id, enabled)  OR
        set_scene_item_visibility(scene, id, enabled)
    - Some wrappers expose name-based helpers; we try those too.
    """
    loop = asyncio.get_running_loop()

    # v5 path: enable/disable by sceneItemId
    if hasattr(OBS, "set_scene_item_enabled"):
        item_id = await _get_scene_item_id_async(scene_name, source_name)
        fn = functools.partial(OBS.set_scene_item_enabled, scene_name, item_id, bool(visible))
        await loop.run_in_executor(None, fn)
        return
    if hasattr(OBS, "set_scene_item_visibility"):
        item_id = await _get_scene_item_id_async(scene_name, source_name)
        fn = functools.partial(OBS.set_scene_item_visibility, scene_name, item_id, bool(visible))
        await loop.run_in_executor(None, fn)
        return

    # Name-based fallback (some wrappers keep convenience sugar)
    if hasattr(OBS, "set_source_visibility"):
        # Note: many wrappers that support names also require the scene
        fn = functools.partial(OBS.set_source_visibility, scene_name, source_name, bool(visible))
        await loop.run_in_executor(None, fn)
        return

    # Generic call() fallback (if available)
    if hasattr(OBS, "call"):
        item_id = await _get_scene_item_id_async(scene_name, source_name)
        payload = {
            "requestType": "SetSceneItemEnabled",
            "requestData": {
                "sceneName": scene_name,
                "sceneItemId": int(item_id),
                "sceneItemEnabled": bool(visible),
            },
        }
        fn = functools.partial(OBS.call, payload)
        await loop.run_in_executor(None, fn)
        return

    raise RuntimeError("OBS manager has no supported visibility method.")

async def _set_text_async(source_name: str, new_text: str):
    """
    Update a text source (timer). Tries your wrapper's set_text first.
    """
    loop = asyncio.get_running_loop()

    if hasattr(OBS, "set_text"):
        fn = functools.partial(OBS.set_text, source_name, new_text)
        await loop.run_in_executor(None, fn)
        return

    # Example generic fallback via call(); adjust for your wrapper if needed:
    if hasattr(OBS, "call"):
        payload = {
            "requestType": "SetInputSettings",
            "requestData": {
                "inputName": source_name,
                "inputSettings": {"text": new_text},
                "overlay": True,
            },
        }
        fn = functools.partial(OBS.call, payload)
        await loop.run_in_executor(None, fn)
        return

    raise RuntimeError("OBS manager has no supported text update method.")

# -----------------------------------------------------------------------------
# Visuals update (left-to-right blue, right-to-left red)
# -----------------------------------------------------------------------------
async def _apply_circle_visibility_async(blue_on: int, red_on: int):
    """
    Turn on the first 'blue_on' blue circles from the LEFT,
    and the first 'red_on' red circles from the RIGHT.
    All others are hidden.
    """
    N = _total_circles
    tasks = []
    for i in range(1, N + 1):
        # Blue grows from left: enable Blue i if i <= blue_on
        blue_visible = i <= blue_on

        # Red grows from right: enable Red i if i > N - red_on  (i.e., i >= N - red_on + 1)
        red_visible = i > (N - red_on)

        tasks.append(_set_item_visibility_async(SCENE_NAME, BLUE_TEMPLATE.format(i=i), blue_visible))
        tasks.append(_set_item_visibility_async(SCENE_NAME, RED_TEMPLATE.format(i=i), red_visible))
    await asyncio.gather(*tasks)

def _fmt_mmss(seconds: int) -> str:
    m = max(0, seconds) // 60
    s = max(0, seconds) % 60
    return f"{m:02d}:{s:02d}"

def _play_progress_if_changed(new_blue_on: int, new_red_on: int):
    global _last_blue_on, _last_red_on
    if new_blue_on != _last_blue_on or new_red_on != _last_red_on:
        try:
            # Play once per “step” change event
            AUDIO.play_audio(SFX_PROGRESS_PATH, False, False, False)
        except Exception as e:
            print(f"[DuelPoll] progress sfx error: {e}")
        _last_blue_on, _last_red_on = new_blue_on, new_red_on

# -----------------------------------------------------------------------------
# Public API
# -----------------------------------------------------------------------------
async def start_duel_poll(duration_seconds: int = 60, total_circles: int = DEFAULT_TOTAL_CIRCLES) -> str:
    """
    Start (or restart) the duel poll.
    - Resets votes
    - Shows 50/50 baseline: left half blue, right half red
    - Starts countdown timer and shows MM:SS in OBS text source
    """
    global _active, _votes, _timer_task, _total_circles, _time_left_s, _last_blue_on, _last_red_on

    async with _lock:
        _votes = {"1": 20, "2": 20}
        _total_circles = max(1, int(total_circles))
        _time_left_s = int(duration_seconds)
        _active = True

        # cancel prior timer if running
        if _timer_task and not _timer_task.done():
            _timer_task.cancel()
            try:
                await _timer_task
            except Exception:
                pass
        _timer_task = asyncio.create_task(_countdown_loop())

        # 50/50 baseline
        half = _total_circles // 2
        blue_on = half
        red_on = _total_circles - half  # if odd, give the extra to the right end

        _last_blue_on, _last_red_on = -1, -1  # force initial render to count as "changed"

    # visuals & timer
    await _set_item_visibility_async("Conference and backdrop", "Vote duel", True)
    await _apply_circle_visibility_async(blue_on, red_on)
    _play_progress_if_changed(blue_on, red_on)  # play once for the initial set
    await _set_text_async(TIMER_SOURCE_NAME, _fmt_mmss(_time_left_s))

    return f"Duel poll started for {duration_seconds}s with {total_circles} circles per side."

async def end_duel_poll(reason: str = "manual"):
    """
    End the duel poll.
    - Stops timer
    - Keeps the final light state as-is
    - Returns (winner, win_ratio) where winner is 1 or 2 (or None on tie/no votes)
    """
    global _active, _timer_task

    async with _lock:
        if not _active:
            return None, 0.0
        _active = False

        if _timer_task and not _timer_task.done():
            _timer_task.cancel()
            try:
                await _timer_task
            except Exception:
                pass
        _timer_task = None

        v1, v2 = _votes["1"], _votes["2"]
        total = v1 + v2
        if total == 0:
            winner = None
            ratio = 0.0
        elif v1 == v2:
            winner = None
            ratio = v1 / total
        else:
            winner = 1 if v1 > v2 else 2
            ratio = max(v1, v2) / total

    # Update timer text to "00:00"
    await _set_text_async(TIMER_SOURCE_NAME, "00:00")
    AUDIO.play_audio(SFX_WIN_PATH, False, False, False)
    print(f"[DuelPoll] Ended ({reason}). Winner={winner} ratio={ratio:.2%}")
    return winner, ratio

def is_duel_active() -> bool:
    return _active

async def duel_poll_state() -> dict:
    async with _lock:
        v1, v2 = _votes["1"], _votes["2"]
        total = v1 + v2
        p1 = (v1 / total) if total else 0.5  # treat no-vote as 50/50 baseline for display
        p2 = (v2 / total) if total else 0.5
        return {
            "active": _active,
            "votes": {"1": v1, "2": v2},
            "ratios": {"1": p1, "2": p2},
            "time_left_s": _time_left_s,
            "total_circles": _total_circles,
        }

# -----------------------------------------------------------------------------
# Vote handling (left vs right growth)
# -----------------------------------------------------------------------------
def is_valid_duel_vote(message: str) -> bool:
    return message.strip() in ("1", "2")

async def record_duel_vote(vote_input: str):
    """
    Count a vote ("1" or "2") if the duel is active; update the circle lights from
    the ends inward; and auto-end if threshold reached (line becomes fully blue or red).
    """
    vote_input = vote_input.strip()

    # First, safely update votes and compute ratios
    async with _lock:
        if not _active:
            return False, "Duel poll is not active."

        if vote_input not in ("1", "2"):
            return False, "Invalid vote. Use '1' or '2'."

        _votes[vote_input] += 1
        v1, v2 = _votes["1"], _votes["2"]
        total = v1 + v2

        # ratios; if no total, stick to 50/50
        if total == 0:
            p1 = p2 = 0.5
        else:
            p1 = v1 / total
            p2 = v2 / total

        if total == 0:
            t1 = t2 = 0.5
        else:
            t1 = p1 / END_THRESHOLD
            t2 = p2 / END_THRESHOLD

        N = _total_circles

        # Desired counts based on ratios
        blue_on = t1 * N
        red_on  = t2 * N

        rounded_blue_on = int(round(blue_on))
        rounded_red_on = int(round(red_on))

        # threshold check
        reached_threshold = (p1 >= END_THRESHOLD) or (p2 >= END_THRESHOLD)
 
    # If threshold reached, fill the whole line with the winner color
    if reached_threshold:
        if p1 >= END_THRESHOLD:
            blue_on, red_on = N, 0
        else:
            blue_on, red_on = 0, N

    # Apply visuals from the ends inward
    await _apply_circle_visibility_async(blue_on, red_on)
    _play_progress_if_changed(rounded_blue_on, rounded_red_on)

    # Auto-end if threshold hit (after visuals are set to full)
    if reached_threshold:
        winner, ratio = await end_duel_poll(reason="threshold")
        return True, f"Auto-ended: Character {winner} reached {ratio:.0%}."

    return True, f"Vote counted. Blue={v1} Red={v2}"


async def hide_duel_poll():
    await _set_item_visibility_async("Conference and backdrop", "Vote duel", False)

# -----------------------------------------------------------------------------
# Countdown timer
# -----------------------------------------------------------------------------
async def _countdown_loop():
    """
    Background task: updates the OBS timer text each second and ends the poll
    when time runs out.
    """
    global _time_left_s

    try:
        while True:
            async with _lock:
                if not _active:
                    break
                remaining = _time_left_s

            # Update timer source
            await _set_text_async(TIMER_SOURCE_NAME, _fmt_mmss(remaining))

            # Sleep ~1s and decrement
            await asyncio.sleep(1.0)
            async with _lock:
                if _active:
                    _time_left_s = max(0, _time_left_s - 1)

            # If we just hit zero, end outside the lock
            if remaining == 0:
                await end_duel_poll(reason="timer")
                break

    except asyncio.CancelledError:
        # Task was cancelled due to end/reset; just exit quietly
        return
