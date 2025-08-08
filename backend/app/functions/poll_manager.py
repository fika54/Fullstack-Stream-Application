# vote_counter.py
import asyncio
from app.functions.obs_websocket import OBSWebsocketsManager

OBS_MANAGER = OBSWebsocketsManager()
_lock = asyncio.Lock()

_votes = {str(i): 0 for i in range(1, 7)}
_poll_active = False


def is_valid_vote(message: str) -> bool:
    try:
        return 1 <= int(message.strip()) <= 6
    except ValueError:
        return False

async def start_poll():
    """
    Starts a new poll and resets all votes.
    """
    global _votes, _poll_active
    async with _lock:
        _votes = {str(i): 0 for i in range(1, 7)}
        _poll_active = True

    for i in range(1, 7):
        await _set_text_async(f"Vote {i}", "0")

    await _set_text_async("Poll Winner", "")
    await _set_filter_visibility_async("Conference and backdrop", "Move vote onscreen", True)

    return "Poll started. All votes have been reset."


async def handle_vote(vote_input: str):
    """
    Handles a vote input if the poll is active.
    
    :param vote_input: A string between '1' and '6'
    :return: A tuple (success: bool, message: str)
    """
    global _votes, _poll_active

    async with _lock:
        if not _poll_active:
            return False, "Poll is not active."

        vote_input = vote_input.strip()

        if vote_input in _votes:
            _votes[vote_input] += 1
            current_votes = _votes[vote_input]
        else:
            return False, "Invalid vote. Must be a number between 1 and 6."

    await _set_text_async(f"Vote {vote_input}", str(current_votes))
    return True, f"Vote counted for Person {vote_input}. Total votes: {current_votes}"


async def end_poll():
    """
    Ends the poll and returns the winner(s).
    
    :return: A tuple (winner_list: list[str], vote_count: int)
    """
    global _poll_active, _votes

    async with _lock:
        if not _poll_active:
            return [], 0

        _poll_active = False
        max_votes = max(_votes.values())

        if max_votes == 0:
            return [], 0

        winners = [k for k, v in _votes.items() if v == max_votes]

    await _set_text_async("Poll Winner", "Poll Ended")
    return winners, max_votes


async def get_vote_totals():
    """
    Returns current vote totals.
    """
    async with _lock:
        return _votes.copy()


async def poll_is_active():
    """
    Returns True if a poll is currently active.
    """
    async with _lock:
        return _poll_active


async def hide_poll():
    """
    Hides the poll from the OBS scene.
    """
    await _set_filter_visibility_async("Conference and backdrop", "Move vote offscreen", True)
    return "Poll hidden."


# ---------------------------------------------
# OBS Calls in Threads (non-async OBS Manager)
# ---------------------------------------------
import functools

async def _set_text_async(source_name, new_text):
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, functools.partial(OBS_MANAGER.set_text, source_name, new_text))

async def _set_filter_visibility_async(source_name, filter_name, filter_enabled):
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, functools.partial(OBS_MANAGER.set_filter_visibility, source_name, filter_name, filter_enabled))