import random
import time

# Make picked lists global
PICKED_TWITCH = set()
PICKED_TIKTOK = set()

class RandomPool:
    def __init__(self, pool_timeout=60):
        # Pools of users with last seen timestamps
        self.TWITCH_POOL = {}  # username: last_seen_timestamp
        self.TIKTOK_POOL = {}

        # Exported selected users (for use in games, overlays, etc.)
        self.LAST_SELECTED = {
            "twitch": None,
            "tiktok": None,
            "either": None
        }

        self.POOL_TIMEOUT = pool_timeout

    # ---- ADD CHATTERS ----

    def add_chatter(self, username: str, platform: str):
        username = username.strip()
        now = time.time()

        if platform == 'twitch':
            self.TWITCH_POOL[username] = now
        elif platform == 'tiktok':
            self.TIKTOK_POOL[username] = now

    def _prune_pool(self, pool: dict):
        now = time.time()
        to_remove = [user for user, ts in pool.items() if now - ts > self.POOL_TIMEOUT]
        for user in to_remove:
            del pool[user]
            # PICKED_TWITCH.discard(user)
            # PICKED_TIKTOK.discard(user)

    # ---- PICKERS ----

    def pick_random_twitch(self):
        self._prune_pool(self.TWITCH_POOL)
        available = set(self.TWITCH_POOL) - PICKED_TWITCH
        if not available:
            return None

        chosen = random.choice(list(available))
        PICKED_TWITCH.add(chosen)
        self.LAST_SELECTED["twitch"] = chosen
        return chosen

    def pick_random_tiktok(self):
        self._prune_pool(self.TIKTOK_POOL)
        available = set(self.TIKTOK_POOL) - PICKED_TIKTOK
        if not available:
            return None

        chosen = random.choice(list(available))
        PICKED_TIKTOK.add(chosen)
        self.LAST_SELECTED["tiktok"] = chosen
        return chosen

    def pick_random_either(self):
        self._prune_pool(self.TWITCH_POOL)
        self._prune_pool(self.TIKTOK_POOL)
        all_available = (set(self.TWITCH_POOL) | set(self.TIKTOK_POOL)) - (PICKED_TWITCH | PICKED_TIKTOK)
        if not all_available:
            return None

        chosen = random.choice(list(all_available))

        if chosen in self.TWITCH_POOL:
            PICKED_TWITCH.add(chosen)
        else:
            PICKED_TIKTOK.add(chosen)

        self.LAST_SELECTED["either"] = chosen
        return chosen

    # ---- RESET FUNCTIONS ----

    def reset_picks(self):
        PICKED_TWITCH.clear()
        PICKED_TIKTOK.clear()
        self.LAST_SELECTED.update({"twitch": None, "tiktok": None, "either": None})

    def clear_all(self):
        self.TWITCH_POOL.clear()
        self.TIKTOK_POOL.clear()
        self.reset_picks()