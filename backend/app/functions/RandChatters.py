import random
import time

# Pools of users with last seen timestamps
TWITCH_POOL = {}  # username: last_seen_timestamp
TIKTOK_POOL = {}

# Keep track of picked users
PICKED_TWITCH = set()
PICKED_TIKTOK = set()

# Exported selected users (for use in games, overlays, etc.)
LAST_SELECTED = {
    "twitch": None,
    "tiktok": None,
    "either": None
}

POOL_TIMEOUT = 60  # seconds

# ---- ADD CHATTERS ----

def add_chatter(username: str, platform: str):
    username = username.strip().lower()
    now = time.time()

    if platform == 'twitch':
        TWITCH_POOL[username] = now
    elif platform == 'tiktok':
        TIKTOK_POOL[username] = now

def _prune_pool(pool: dict):
    now = time.time()
    to_remove = [user for user, ts in pool.items() if now - ts > POOL_TIMEOUT]
    for user in to_remove:
        del pool[user]
        PICKED_TWITCH.discard(user)
        PICKED_TIKTOK.discard(user)

# ---- PICKERS ----

def pick_random_twitch():
    _prune_pool(TWITCH_POOL)
    available = set(TWITCH_POOL) - PICKED_TWITCH
    if not available:
        return None

    chosen = random.choice(list(available))
    PICKED_TWITCH.add(chosen)
    LAST_SELECTED["twitch"] = chosen
    return chosen

def pick_random_tiktok():
    _prune_pool(TIKTOK_POOL)
    available = set(TIKTOK_POOL) - PICKED_TIKTOK
    if not available:
        return None

    chosen = random.choice(list(available))
    PICKED_TIKTOK.add(chosen)
    LAST_SELECTED["tiktok"] = chosen
    return chosen

def pick_random_either():
    _prune_pool(TWITCH_POOL)
    _prune_pool(TIKTOK_POOL)
    all_available = (set(TWITCH_POOL) | set(TIKTOK_POOL)) - (PICKED_TWITCH | PICKED_TIKTOK)
    if not all_available:
        return None

    chosen = random.choice(list(all_available))

    if chosen in TWITCH_POOL:
        PICKED_TWITCH.add(chosen)
    else:
        PICKED_TIKTOK.add(chosen)

    LAST_SELECTED["either"] = chosen
    return chosen

# ---- RESET FUNCTIONS ----

def reset_picks():
    PICKED_TWITCH.clear()
    PICKED_TIKTOK.clear()
    LAST_SELECTED.update({"twitch": None, "tiktok": None, "either": None})

def clear_all():
    TWITCH_POOL.clear()
    TIKTOK_POOL.clear()
    reset_picks()