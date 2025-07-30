from app.functions.audio_player import AudioManager
from app.functions.obs_websocket import OBSWebsocketsManager
from app.functions.text_to_speech import TTSManager

class VoiceManager:
    tts_manager = TTSManager()
    audio_manager = AudioManager()
    obswebsockets_manager = OBSWebsocketsManager()

    user1_voice_name = "af_bella"
    user2_voice_name = "am_michael"
    user3_voice_name = "bf_isabella"

    def __init__(self):
        file_path = self.tts_manager.text_to_audio("Chat Clash App is now running!") # Say some shit when the app starts
        self.audio_manager.play_audio(file_path, True, True, True)

    def update_voice_name(self, user_number, voice_name):
        if user_number == "1":
            self.user1_voice_name = voice_name
        elif user_number == "2":
            self.user2_voice_name = voice_name
        elif user_number == "3":
            self.user3_voice_name = voice_name

    def text_to_audio(self, text, user_number):
        if user_number == "1":
            voice_name = self.user1_voice_name
        elif user_number == "2":
            voice_name = self.user2_voice_name
        # elif user_number == "3":
        #     voice_name = self.user3_voice_name

        tts_file = self.tts_manager.text_to_audio(text, voice_name)

        # OPTIONAL: Use OBS Websockets to enable the Move plugin filter
        if user_number == "1":
            self.obswebsockets_manager.set_filter_visibility("Line In", "Audio Move - Character 1", True)
        elif user_number == "2":
            self.obswebsockets_manager.set_filter_visibility("Line In", "Audio Move - Character 2", True)
        # elif user_number == "3":
        #     self.obswebsockets_manager.set_filter_visibility("Line In", "Audio Move - DnD Player 3", True)

        self.audio_manager.play_audio(tts_file, True, True, True)

        if user_number == "1":
            self.obswebsockets_manager.set_filter_visibility("Line In", "Audio Move - Character 1", False)
        elif user_number == "2":
            self.obswebsockets_manager.set_filter_visibility("Line In", "Audio Move - Character 2", False)
        # elif user_number == "3":
        #     self.obswebsockets_manager.set_filter_visibility("Line In", "Audio Move - DnD Player 3", False)