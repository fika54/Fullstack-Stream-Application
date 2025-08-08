from app.functions.audio_player import AudioManager
from app.functions.obs_websocket import OBSWebsocketsManager
from app.functions.text_to_speech import TTSManager

class VoiceManager:
    tts_manager = TTSManager()
    audio_manager = AudioManager()
    obswebsockets_manager = OBSWebsocketsManager()

    def __init__(self):
        file_path = self.tts_manager.text_to_audio("The Chat Conference App is now running!") # Say some shit when the app starts
        self.audio_manager.play_audio(file_path, True, True, True)

    def text_to_audio(self, text, user_number, voice_name):
        tts_file = self.tts_manager.text_to_audio(text, voice_name)

        # OPTIONAL: Use OBS Websockets to enable the Move plugin filter
        self.obswebsockets_manager.set_filter_visibility("Line In", f"Audio Move - Character {user_number}", True)

        self.audio_manager.play_audio(tts_file, True, True, True)

        self.obswebsockets_manager.set_filter_visibility("Line In", f"Audio Move - Character {user_number}", False)