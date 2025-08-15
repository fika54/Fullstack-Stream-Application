# chancegame.py
import asyncio
import functools
import random
from typing import Optional, Set

from app.functions.audio_player import AudioManager
from app.functions.obs_websocket import OBSWebsocketsManager

# ----------------------------
# Singletons / constants
# ----------------------------
AUDIO_MANAGER = AudioManager()
OBS_MANAGER = OBSWebsocketsManager()

# Scene and source name templates (edit if your OBS names differ)
CRATES_SCENE_NAME = "Crate Game"          # <-- change to your actual scene name if needed
CRATE_NAME_TEMPLATE = "Crate {i}"         # expects: crate 1, crate 2, ... crate 12
BOMB_NAME_TEMPLATE = "Bomb {i}"           # expects: bomb 1, bomb 2, ... bomb 12

# Sound effects (edit paths if needed)
SFX_EMPTY = "app/Sound effects/empty_gun_shot.mp3"
SFX_GUN = "app/Sound effects/gun_shot.mp3"
SFX_DRUMROLL = "app/Sound effects/Drum_Roll.mp3"
SFX_SAFE = "app/Sound effects/Safe_Crate.mp3"
SFX_EXPLOSION = "app/Sound effects/Explosion.mp3"

# ----------------------------
# Async helpers (non-blocking)
# ----------------------------
async def _play_audio_async(*args, **kwargs):
    """Run potentially blocking audio playback in a thread."""
    loop = asyncio.get_running_loop()
    func = functools.partial(AUDIO_MANAGER.play_audio, *args, **kwargs)
    await loop.run_in_executor(None, func)

# Detect which visibility API the OBS manager exposes.
_HAS_SOURCE_VIS = hasattr(OBS_MANAGER, "set_source_visibility")
_HAS_SCENE_ITEM_VIS = hasattr(OBS_MANAGER, "set_scene_item_visibility")

async def _set_item_visibility_async(source_name: str, visible: bool, scene_name: Optional[str] = None):
    """
    Toggle visibility for a source. Tries multiple common OBSWebsocketsManager APIs:
      - set_scene_item_visibility(scene_name, source_name, visible)
      - set_source_visibility(source_name, visible)
    """
    loop = asyncio.get_running_loop()

    if _HAS_SCENE_ITEM_VIS and scene_name:
        func = functools.partial(OBS_MANAGER.set_scene_item_visibility, scene_name, source_name, visible)
        await loop.run_in_executor(None, func)
        return

    if _HAS_SOURCE_VIS:
        func = functools.partial(OBS_MANAGER.set_source_visibility,scene_name, source_name, visible)
        await loop.run_in_executor(None, func)
        return

    # If your OBS manager uses a different method name, update here:
    raise RuntimeError(
        "OBSWebsocketsManager has no supported visibility method. "
        "Expected set_scene_item_visibility(scene, source, visible) or set_source_visibility(source, visible)."
    )

async def _set_filter_visibility_async(filter_name: str, visible: bool, scene_name: Optional[str] = None):
    """
    Toggle visibility for a source. Tries multiple common OBSWebsocketsManager APIs:
      - set_scene_item_visibility(scene_name, source_name, visible)
      - set_source_visibility(source_name, visible)
    """
    loop = asyncio.get_running_loop()

    try:    
        func = functools.partial(OBS_MANAGER.set_filter_visibility, scene_name, filter_name, visible)
        await loop.run_in_executor(None, func)
        return
    except Exception as e:
        print(f"Error setting filter visibility: {e}")

def _crate_name(i: int) -> str:
    return CRATE_NAME_TEMPLATE.format(i=i)

def _bomb_name(i: int) -> str:
    return BOMB_NAME_TEMPLATE.format(i=i)

# =========================================================
# Game 1: Russian Roulette (50/50)
# =========================================================
current_player = 1
Roulettelock = asyncio.Lock()

async def shoot_gun():
    """
    50/50: either gun fires or empty click.
    """
    global current_player
    rand = random.randint(1, 2)
    status = ""
    if rand != 1:
        await _play_audio_async(SFX_EMPTY, False, False, False)
        status = "Gun empty"
    else:
        await _play_audio_async(SFX_GUN, False, False, False)
        status = "Gun fired"
    

    

    return status

async def flip_gun():
    global current_player

    if current_player == 1:
        await _set_filter_visibility_async("Flip gun right", True, "Conference and backdrop")
        current_player = 2
    else:
        await _set_filter_visibility_async("Flip gun left", True, "Conference and backdrop")
        current_player = 1

    return f"Gun flipped to player {current_player}."

hidden = False

async def hide_gun():
    global hidden
    """
    Hides the gun from the OBS scene.
    """
    if hidden:
        await _set_item_visibility_async("gun", True, "Conference and backdrop")
        hidden = False
    else:
        await _set_item_visibility_async("gun", False, "Conference and backdrop")
        hidden = True
    return "Gun hidden from view."

# =========================================================
# Game 2: Crates (1 of 12 has a bomb)
# =========================================================
# State
_crates_lock = asyncio.Lock()
_crates_active: bool = False
_hidden_bomb_index: Optional[int] = None
_opened_crates: Set[int] = set()

async def start_crates_game(scene_name: str = CRATES_SCENE_NAME) -> str:
    """
    Starts a new Crates game:
      - Shows all 12 crates (crate 1..12).
      - Hides all bombs (bomb 1..12) EXCEPT one randomly chosen bomb which is made visible.
    """
    global _crates_active, _hidden_bomb_index, _opened_crates

    async with _crates_lock:
        _crates_active = True
        _opened_crates = set()
        _hidden_bomb_index = random.randint(1, 12)

        # Show all crates, hide all bombs
        tasks = []
        for i in range(1, 13):
            tasks.append(_set_item_visibility_async(_crate_name(i), True, scene_name))
            tasks.append(_set_item_visibility_async(_bomb_name(i), False, scene_name))
        await asyncio.gather(*tasks)
        # Enable the one bomb that's actually under a crate
        await _set_item_visibility_async(_bomb_name(_hidden_bomb_index), True, scene_name)


    return "Crates game started. A bomb has been hidden."

async def select_crate(crate_number: int, scene_name: str = CRATES_SCENE_NAME) -> str:
    """
    Handles a player's crate selection:
      - Plays a drumroll.
      - 'Opens' the crate by hiding the crate source.
      - If the selected crate has the bomb: play explosion and end game.
        Otherwise: play 'safe' sound and continue.
    """
    global _crates_active, _hidden_bomb_index, _opened_crates

    if not (1 <= crate_number <= 12):
        return "Invalid crate number. Choose 1–12."

    async with _crates_lock:
        if not _crates_active:
            return "Crates game is not active. Start a new game first."

        if crate_number in _opened_crates:
            return f"Crate {crate_number} is already opened."

        # Mark as opened right away to avoid race conditions
        _opened_crates.add(crate_number)

    # Play the suspense
    await _play_audio_async(SFX_DRUMROLL, True, False, False)

    # 'Open' the crate by hiding it (reveals whatever is underneath)
    await _set_item_visibility_async(_crate_name(crate_number), False, scene_name)

    # Check if this crate had the bomb (that bomb source was set visible at start)
    is_bomb = (crate_number == _hidden_bomb_index)

    if is_bomb:
        await _play_audio_async(SFX_EXPLOSION, False, False, False)
        async with _crates_lock:
            _crates_active = False
        return f"💥 Boom! Crate {crate_number} had the bomb. Game over."
    else:
        await _play_audio_async(SFX_SAFE, False, False, False)
        return f"✅ Safe! Crate {crate_number} was empty."

async def reset_crates(scene_name: str = CRATES_SCENE_NAME) -> str:
    """
    Resets the Crates game visuals (hides everything) and clears state.
    """
    global _crates_active, _hidden_bomb_index, _opened_crates

    async with _crates_lock:
        _crates_active = False
        _hidden_bomb_index = None
        _opened_crates = set()

    tasks = []
    for i in range(1, 13):
        tasks.append(_set_item_visibility_async(_crate_name(i), False, scene_name))
        tasks.append(_set_item_visibility_async(_bomb_name(i), False, scene_name))
    await asyncio.gather(*tasks)

    return "Crates game has been reset."
