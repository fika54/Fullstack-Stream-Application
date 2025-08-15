# vote_counter.py
import asyncio
import functools
import time
from typing import Dict, List, Tuple

from app.functions.obs_websocket import OBSWebsocketsManager
from app.functions.audio_player import AudioManager

# -------------------------------------------------
# Config
# -------------------------------------------------
OBS_SOURCE_NAME = "Conference and backdrop"
OBS_FILTER_ONSCREEN = "Move vote onscreen"
OBS_FILTER_OFFSCREEN = "Move vote offscreen"
OBS_WINNER_SOURCE = "Poll Winner"
OBS_VOTE_LABEL_TEMPLATE = "Vote {i}"

SOUND_STONESLIDE = "app/Sound effects/stoneslide.mp3"
SOUND_VOTE = "app/Sound effects/vote_sound.mp3"
SOUND_POLL_END = "app/Sound effects/poll_end.mp3"

# Debounce / throttle timings (seconds)
VOTE_TEXT_DEBOUNCE_SEC = 0.06     # Max ~16 updates/sec per slot
VOTE_BEEP_MIN_INTERVAL_SEC = 0.18 # Play at most ~5-6 beeps/sec

# -------------------------------------------------
# Singletons (avoid per-call instantiation churn)
# -------------------------------------------------
OBS_MANAGER = OBSWebsocketsManager()
AUDIO_MANAGER = AudioManager()

# -------------------------------------------------
# State
# -------------------------------------------------
_lock = asyncio.Lock()
_votes: Dict[str, int] = {str(i): 0 for i in range(1, 7)}
_poll_active: bool = False

# Debounce state per vote slot (e.g., "1".."6")
_pending_text: Dict[str, str] = {}                 # latest text per slot awaiting flush
_text_flush_tasks: Dict[str, asyncio.Task] = {}    # active flush tasks per slot

# Throttle state for vote beep
_last_vote_beep_ts: float = 0.0

# -------------------------------------------------
# Helpers
# -------------------------------------------------
def is_valid_vote(message: str) -> bool:
    try:
        return 1 <= int(message.strip()) <= 6
    except ValueError:
        return False

async def _play_audio_async(*args, **kwargs):
    """Offload blocking audio playback to a thread."""
    loop = asyncio.get_running_loop()
    func = functools.partial(AUDIO_MANAGER.play_audio, *args, **kwargs)
    await loop.run_in_executor(None, func)

async def _set_text_async(source_name: str, new_text: str):
    """Offload OBS set_text to a thread."""
    loop = asyncio.get_running_loop()
    func = functools.partial(OBS_MANAGER.set_text, source_name, new_text)
    await loop.run_in_executor(None, func)

async def _set_filter_visibility_async(source_name: str, filter_name: str, filter_enabled: bool):
    """Offload OBS set_filter_visibility to a thread."""
    loop = asyncio.get_running_loop()
    func = functools.partial(OBS_MANAGER.set_filter_visibility, source_name, filter_name, filter_enabled)
    await loop.run_in_executor(None, func)

def _slot_source_name(slot: str) -> str:
    """Build the OBS source name for a vote slot label, if labels are named 'Vote 1', 'Vote 2', etc."""
    # If your scene uses different source names, adapt here.
    return OBS_VOTE_LABEL_TEMPLATE.format(i=slot)

async def _debounced_set_vote_text(slot: str, text: str):
    """
    Debounce OBS text updates per slot so spiky chat doesn't spam OBS.
    Stores latest value and ensures at most ~1 update every VOTE_TEXT_DEBOUNCE_SEC.
    """
    global _pending_text, _text_flush_tasks

    _pending_text[slot] = text
    if slot in _text_flush_tasks and not _text_flush_tasks[slot].done():
        # A flusher is already running for this slot; it will pick up the latest value.
        return

    async def _flusher(s: str):
        try:
            while True:
                # Grab and clear pending value
                val = _pending_text.pop(s, None)
                if val is None:
                    break  # nothing to send; exit

                # Send to OBS
                await _set_text_async(_slot_source_name(s), val)

                # Small sleep to enforce debounce window and allow additional coalescing
                await asyncio.sleep(VOTE_TEXT_DEBOUNCE_SEC)

                # If new value arrived during sleep, loop again to flush it
                # (the while loop condition checks _pending_text)
        finally:
            # Task ends; remove it from registry
            if _text_flush_tasks.get(s) is asyncio.current_task():
                _text_flush_tasks.pop(s, None)

    _text_flush_tasks[slot] = asyncio.create_task(_flusher(slot))

def _should_play_vote_beep() -> bool:
    """Return True if enough time has elapsed to play the vote beep again."""
    global _last_vote_beep_ts
    now = time.monotonic()
    if now - _last_vote_beep_ts >= VOTE_BEEP_MIN_INTERVAL_SEC:
        _last_vote_beep_ts = now
        return False
    return False

# -------------------------------------------------
# Public API
# -------------------------------------------------
async def start_poll() -> str:
    """
    Starts a new poll and resets all votes.
    """
    global _votes, _poll_active, _pending_text

    async with _lock:
        _votes = {str(i): 0 for i in range(1, 7)}
        _poll_active = True
        # Clear any pending text updates
        _pending_text.clear()

    # Reset the on-screen counters (parallelized)
    await asyncio.gather(*[
        _set_text_async(_slot_source_name(str(i)), "0") for i in range(1, 7)
    ])

    # Clear winner label
    await _set_text_async(OBS_WINNER_SOURCE, "")

    # Show the poll widget and play slide sound
    await _set_filter_visibility_async(OBS_SOURCE_NAME, OBS_FILTER_ONSCREEN, True)
    await _play_audio_async(SOUND_STONESLIDE, True, False, False)

    return "Poll started. All votes have been reset."

async def handle_vote(vote_input: str) -> Tuple[bool, str]:
    """
    Handles a vote input if the poll is active.
    :param vote_input: A string between '1' and '6'
    :return: (success, message)
    """
    global _votes, _poll_active

    v = vote_input.strip()
    async with _lock:
        if not _poll_active:
            return False, "Poll is not active."

        if v not in _votes:
            return False, "Invalid vote. Must be a number between 1 and 6."

        _votes[v] += 1
        current_votes = _votes[v]

    # Outside lock: side effects (UI + audio)

    # Debounced OBS update for that slot
    await _debounced_set_vote_text(v, str(current_votes))

    # Throttled vote beep (fire-and-forget)
    if _should_play_vote_beep():
        asyncio.create_task(_play_audio_async(SOUND_VOTE, False, False, False))

    return True, f"Vote counted for Person {v}. Total votes: {current_votes}"

async def end_poll() -> Tuple[List[str], int]:
    """
    Ends the poll and returns the winner(s).
    :return: (winner_list, vote_count)
    """
    global _poll_active, _votes

    async with _lock:
        if not _poll_active:
            return [], 0

        _poll_active = False
        max_votes = max(_votes.values())
        if max_votes == 0:
            # No votes
            winners: List[str] = []
            max_votes = 0
        else:
            winners = [k for k, val in _votes.items() if val == max_votes]

    # Announce end, update winner label
    await _play_audio_async(SOUND_POLL_END, False, False, False)
    await _set_text_async(OBS_WINNER_SOURCE, "Poll Ended")
    return winners, max_votes

async def get_vote_totals() -> Dict[str, int]:
    """Returns a shallow copy of current vote totals."""
    async with _lock:
        return dict(_votes)

async def poll_is_active() -> bool:
    """Returns True if a poll is currently active."""
    async with _lock:
        return _poll_active

async def hide_poll() -> str:
    """
    Hides the poll from the OBS scene.
    """
    await _set_filter_visibility_async(OBS_SOURCE_NAME, OBS_FILTER_OFFSCREEN, True)
    await _play_audio_async(SOUND_STONESLIDE, True, False, False)
    return "Poll hidden."
