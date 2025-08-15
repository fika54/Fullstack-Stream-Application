from app.functions.RandChatters import RandomPool
from app.functions.voice_manager import VoiceManager
from app.functions.obs_websocket import OBSWebsocketsManager
from app.functions.audio_player import AudioManager

VOICE_MANAGER = VoiceManager()
OBS_MANAGER = OBSWebsocketsManager()
AUDIO_MANAGER = AudioManager()

MUTE_TTS = False  # Set to True to mute TTS audio

CHARACTERS = {}  # {number: {username: platform}}
CHARACTER_VOICE_STYLES = {}  # {number: voice_style}
CHARACTER_POOLS = {}  # {number: RandomPool}

DEFAULT_VOICE_STYLES = [
    'af_bella', 'am_michael', 'af_nicole', 'af_sarah', 'af_sky',
    'am_adam', 'bf_emma', 'bf_isabella', 'bm_george', 'bm_lewis'
]

MAX_CHARACTERS = 10


def ensure_character(number):
    if number < 1 or number > MAX_CHARACTERS:
        raise ValueError(f"Character number must be between 1 and {MAX_CHARACTERS}")
    if number not in CHARACTERS:
        CHARACTERS[number] = {}
    if number not in CHARACTER_VOICE_STYLES:
        # Cycle through defaults if more than available
        CHARACTER_VOICE_STYLES[number] = DEFAULT_VOICE_STYLES[(number-1) % len(DEFAULT_VOICE_STYLES)]
    if number not in CHARACTER_POOLS:
        CHARACTER_POOLS[number] = RandomPool()


async def set_character(number: int, username: str, platform: str):
    ensure_character(number)
    CHARACTERS[number] = {username: platform}
    print(f"Character {number} set to: {CHARACTERS[number]}")
    OBS_MANAGER.set_text(f"Character {number} Name", username)
    OBS_MANAGER.set_source_visibility("Chat Conference",f"Character {number} Scene", True)
    OBS_MANAGER.set_source_visibility("Voting board",f"Vote {number}", True)


async def pick_character(number: int, platform: str):
    ensure_character(number)
    pool = CHARACTER_POOLS[number]
    if platform == "twitch":
        username = pool.pick_random_twitch()
        actual_platform = "twitch"
    elif platform == "tiktok":
        username = pool.pick_random_tiktok()
        actual_platform = "tiktok"
    else:
        username = pool.pick_random_either()
        if username in pool.TWITCH_POOL:
            actual_platform = "twitch"
        elif username in pool.TIKTOK_POOL:
            actual_platform = "tiktok"
        else:
            actual_platform = None
    if username and actual_platform:
        await set_character(number, username, actual_platform)
    else:
        print(f"No available character to pick for Character {number}.")
    return username


async def update_character_voice_style(number: int, voice_style: str):
    ensure_character(number)
    CHARACTER_VOICE_STYLES[number] = voice_style
    print(f"Updated Character {number} voice style to {voice_style}")


def speak_character_message(number: int, username: str, platform: str, message: str):
    ensure_character(number)
    char = CHARACTERS.get(number, {})
    if char and username in char and char[username] == platform:
        OBS_MANAGER.set_text(f"Character {number} Text", message)

        if not MUTE_TTS:
            print(f"Speaking as Character {number} ({username}, {platform}): {message}")
            voice_style = CHARACTER_VOICE_STYLES.get(number, DEFAULT_VOICE_STYLES[0])
            VOICE_MANAGER.text_to_audio(message, number, voice_style)
    else:
        print(f"Character {number} is not set or username/platform mismatch.")


def handle_chatter_message(username: str, platform: str, message: str):
    for number, char in CHARACTERS.items():
        if char and username in char and char[username] == platform:
            speak_character_message(number, username, platform, message)
            return True
    return False


async def remove_character(number: int):
    ensure_character(number)
    CHARACTERS[number] = {}
    OBS_MANAGER.set_text(f"Character {number} Name", f"Deceased")
    OBS_MANAGER.set_text(f"Character {number} Text", "")
    OBS_MANAGER.set_source_visibility("Chat Conference",f"Character {number} Scene", False)
    OBS_MANAGER.set_source_visibility("Voting board",f"Vote {number}", False)
    AUDIO_MANAGER.play_audio("app/Sound effects/gun_shot.mp3", False, False, False)


async def reset_character_pool(number: int):
    ensure_character(number)
    CHARACTER_POOLS[number].clear_all()


def reset_all_pools():
    for pool in CHARACTER_POOLS.values():
        pool.clear_all()


def add_chatter_to_character_pool(number: int, username: str, platform: str):
    """
    Adds a chatter to the specified character's pool.
    """
    ensure_character(number)
    CHARACTER_POOLS[number].add_chatter(username, platform)
    print(f"Added {username} ({platform}) to Character {number} pool.")

async def mute_character_tts(mute: bool):
    """
    Mutes or unmutes the TTS audio.
    """
    global MUTE_TTS
    MUTE_TTS = mute
    VOICE_MANAGER.reset()  # Clear any queued TTS jobs
    status = "muted" if mute else "unmuted"
    print(f"TTS audio is now {status}.")
    return status

def message_as_character(number: int, message: str, alias: str):
    """
    Sends a message as the specified character.
    """
    try:
        OBS_MANAGER.set_source_visibility("Chat Conference",f"Character {number} Scene", True)
        ensure_character(number)
        OBS_MANAGER.set_text(f"Character {number} Name", alias)
        voice_style = CHARACTER_VOICE_STYLES.get(number, DEFAULT_VOICE_STYLES[0])
        
        OBS_MANAGER.set_text(f"Character {number} Text", message)
        VOICE_MANAGER.text_to_audio(message, number, voice_style)
    except Exception as e:
        print(f"Error sending message as character {number}: {e}")
