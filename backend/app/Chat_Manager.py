from app.functions.RandChatters import RandomPool
from app.functions.voice_manager import VoiceManager
from app.functions.obs_websocket import OBSWebsocketsManager

VOICE_MANAGER = VoiceManager()
OBS_MANAGER = OBSWebsocketsManager()

CHARACTER_1 = {}  # {username: platform}
CHARACTER_2 = {}

CHARACTER_1_VOICE_STYLE = "af_bella"
CHARACTER_2_VOICE_STYLE = "am_michael"

CHARACTER_POOL_1 = RandomPool()
CHARACTER_POOL_2 = RandomPool()


def set_character_1(username: str, platform: str):
    global CHARACTER_1
    CHARACTER_1 = {username: platform}
    print(f"Character 1 set to: {CHARACTER_1}")
    OBS_MANAGER.set_text("Character 1 Name", username)


def set_character_2(username: str, platform: str):
    global CHARACTER_2
    CHARACTER_2 = {username: platform}
    print(f"Character 2 set to: {CHARACTER_2}")
    OBS_MANAGER.set_text("Character 2 Name", username)


def pick_character_1(platform: str):
    """
    Picks a random character from CHARACTER_POOL_1 based on the platform.
    platform: "twitch", "tiktok", or "either"
    """
    if platform == "twitch":
        username = CHARACTER_POOL_1.pick_random_twitch()
        actual_platform = "twitch"
    elif platform == "tiktok":
        username = CHARACTER_POOL_1.pick_random_tiktok()
        actual_platform = "tiktok"
    else:
        username = CHARACTER_POOL_1.pick_random_either()
        # Determine actual platform
        if username in CHARACTER_POOL_1.TWITCH_POOL:
            actual_platform = "twitch"
        elif username in CHARACTER_POOL_1.TIKTOK_POOL:
            actual_platform = "tiktok"
        else:
            actual_platform = None
    if username and actual_platform:
        set_character_1(username, actual_platform)
    else:
        print("No available character to pick for Character 1.")
    return username


def pick_character_2(platform: str):
    """
    Picks a random character from CHARACTER_POOL_2 based on the platform.
    platform: "twitch", "tiktok", or "either"
    """
    if platform == "twitch":
        username = CHARACTER_POOL_2.pick_random_twitch()
        actual_platform = "twitch"
    elif platform == "tiktok":
        username = CHARACTER_POOL_2.pick_random_tiktok()
        actual_platform = "tiktok"
    else:
        username = CHARACTER_POOL_2.pick_random_either()
        # Determine actual platform
        if username in CHARACTER_POOL_2.TWITCH_POOL:
            actual_platform = "twitch"
        elif username in CHARACTER_POOL_2.TIKTOK_POOL:
            actual_platform = "tiktok"
        else:
            actual_platform = None
    if username and actual_platform:
        set_character_2(username, actual_platform)
    else:
        print("No available character to pick for Character 2.")
    return username


def update_character_voice_style(character_number: int, voice_style: str):
    """
    Updates the voice style for the given character number.
    """
    global CHARACTER_1_VOICE_STYLE, CHARACTER_2_VOICE_STYLE
    if character_number == 1:
        CHARACTER_1_VOICE_STYLE = voice_style
        VOICE_MANAGER.update_voice_name("1", voice_style)
        print(f"Updated Character 1 voice style to {voice_style}")
    elif character_number == 2:
        CHARACTER_2_VOICE_STYLE = voice_style
        VOICE_MANAGER.update_voice_name("2", voice_style)
        print(f"Updated Character 2 voice style to {voice_style}")


def speak_character_1_message(username: str, platform: str, message: str):
    """
    Speaks the given message using Character 1's voice and updates OBS text.
    Only if both username and platform match Character 1.
    """
    if CHARACTER_1 and username in CHARACTER_1 and CHARACTER_1[username] == platform:
        OBS_MANAGER.set_text("Character 1 Text", message)
        print(f"Speaking as Character 1 ({username}, {platform}): {message}")
        VOICE_MANAGER.text_to_audio(message, user_number="1")
    else:
        print("Character 1 is not set or username/platform mismatch.")


def speak_character_2_message(username: str, platform: str, message: str):
    """
    Speaks the given message using Character 2's voice and updates OBS text.
    Only if both username and platform match Character 2.
    """
    if CHARACTER_2 and username in CHARACTER_2 and CHARACTER_2[username] == platform:
        OBS_MANAGER.set_text("Character 2 Text", message)
        print(f"Speaking as Character 2 ({username}, {platform}): {message}")
        VOICE_MANAGER.text_to_audio(message, user_number="2")
    else:
        print("Character 2 is not set or username/platform mismatch.")


def handle_chatter_message(username: str, platform: str, message: str):
    """
    Checks if the username and platform match Character 1 or Character 2 and makes the respective character speak.
    Returns True if a character spoke, False otherwise.
    """
    if CHARACTER_1 and username in CHARACTER_1 and CHARACTER_1[username] == platform:
        speak_character_1_message(username, platform, message)
        return True
    if CHARACTER_2 and username in CHARACTER_2 and CHARACTER_2[username] == platform:
        speak_character_2_message(username, platform, message)
        return True
    return False


def remove_character_1():
    """
    Removes Character 1, resets OBS name to 'Character 1', and clears CHARACTER_1.
    """
    global CHARACTER_1
    CHARACTER_1 = {}
    OBS_MANAGER.set_text("Character 1 Name", "Character 1")
    OBS_MANAGER.set_text("Character 1 Text", "")


def remove_character_2():
    """
    Removes Character 2, resets OBS name to 'Character 2', and clears CHARACTER_2.
    """
    global CHARACTER_2
    CHARACTER_2 = {}
    OBS_MANAGER.set_text("Character 2 Name", "Character 2")
    OBS_MANAGER.set_text("Character 2 Text", "")


def reset_all_pools():
    """
    Resets the picked pools and the current pool of chatters for both character pools.
    """
    CHARACTER_POOL_1.clear_all()
    CHARACTER_POOL_2.clear_all()


def reset_character_1_pool():
    """
    Resets the picked pool and the current pool of chatters for Character 1 only.
    """
    CHARACTER_POOL_1.clear_all()


def reset_character_2_pool():
    """
    Resets the picked pool and the current pool of chatters for Character 2 only.
    """
    CHARACTER_POOL_2.clear_all()