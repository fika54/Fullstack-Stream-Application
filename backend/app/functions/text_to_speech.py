import os
import random
import pygame
from piper import PiperVoice
from kokoro_onnx import Kokoro
import soundfile as sf
import wave
import time

# Path to your Piper models folder
MODELS_DIR = os.path.join(os.path.dirname(__file__), "voiceModels")
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "chatMsgOutput")


class TTSManager:
    def __init__(self):
        pygame.init()
        # Preload PiperVoice objects for each model, using both model and config file
        self.voices = {}
        print("Loading TTS model...")#

        model_location = os.path.join(MODELS_DIR, "kokoro-v0_19.onnx")
        voices_location = os.path.join(MODELS_DIR, "voices.bin")

        # Initialize Kokoro
        self.kokoro = Kokoro(model_location, voices_location)
        
        # Available voices
        self.voices = [
            'af', 'af_bella', 'af_nicole', 'af_sarah', 'af_sky',
            'am_adam', 'am_michael', 'bf_emma', 'bf_isabella',
            'bm_george', 'bm_lewis'
        ]


    def text_to_audio(self, text: str, voice="random", speed=1.0):
        if not text or not text.strip():
            print("This message was empty")
            return None

        # Choose a model
        if voice == "random":
            model = random.choice(self.voices)
        elif voice in self.voices:
            model = voice
        else:
            # fallback to first model if not found
            model = self.voices[0]

        try:
            # Generate audio
            samples, sample_rate = self.kokoro.create(
                text,
                voice=model,
                speed=float(speed)
            )
            
            # Create temporary file
            #temp_dir = tempfile.mkdtemp()
            output_path = os.path.join(
                OUTPUT_DIR,
                f"_Msg{str(hash(text))}_{model.replace('.onnx','')}.wav"
            )
            
            # Save to temporary file
            sf.write(output_path, samples, sample_rate)

            return output_path
        except Exception as e:
            return f"Error: {str(e)}"
    
    def play_audio(self, file_path):
        """
        Play the generated audio file using Pygame.
        """
        if not os.path.exists(file_path):
            print(f"Audio file does not exist: {file_path}")
            return

        pygame.mixer.init()
        pygame.mixer.music.load(file_path)
        pygame.mixer.music.play()

        # Wait until the audio is done playing
        while pygame.mixer.music.get_busy():
            pygame.time.Clock().tick(10)

        # Unload the music to release the file handle
        pygame.mixer.music.unload()

        # Small delay to ensure OS releases the file lock
        time.sleep(0.1)

        # Optionally delete the file after playback
        try:
            os.remove(file_path)
            print(f"Deleted the audio file: {file_path}")
        except PermissionError:
            print(f"Couldn't remove {file_path} because it is being used by another process.")
        

        #print(f"Finished playing: {file_path}")

# Tests here
if __name__ == '__main__':
    tts_manager = TTSManager()
    pygame.mixer.init()

    file_path = tts_manager.text_to_audio("Here's my test audio!!", "bm_lewis", 1.0)
    tts_manager.play_audio(file_path)

    while True:
        stuff_to_say = input("\nNext question? \n\n")
        if len(stuff_to_say) == 0:
            continue
        file_path = tts_manager.text_to_audio(stuff_to_say, "jenny.onnx")
        tts_manager.play_audio(file_path)