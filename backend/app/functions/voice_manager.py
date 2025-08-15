import threading
import queue
import time
from app.functions.audio_player import AudioManager
from app.functions.obs_websocket import OBSWebsocketsManager
from app.functions.text_to_speech import TTSManager


class VoiceManager:
    """
    Queued, single-threaded TTS playback manager.
    - Call text_to_audio(text, user_number, voice_name) to enqueue a message.
    - A dedicated worker thread consumes the queue and plays items sequentially.
    - OBS filter visibility is toggled per message around playback.
    """

    def __init__(self, start_message: str = "The Chat Conference App is now running!"):
        self.tts_manager = TTSManager()
        self.audio_manager = AudioManager()
        self.obswebsockets_manager = OBSWebsocketsManager()

        # Thread-safe FIFO queue of playback jobs
        self._queue: "queue.Queue[dict]" = queue.Queue()

        # Event to allow graceful shutdown if needed
        self._stop_event = threading.Event()

        # Start the worker thread
        self._worker = threading.Thread(target=self._worker_loop, name="VoiceManagerWorker", daemon=True)
        self._worker.start()

        # Enqueue the startup message instead of playing immediately
        self.text_to_audio(start_message, user_number=0, voice_name=None)

    def text_to_audio(self, text, user_number: int, voice_name: str | None):
        """
        Public API: enqueue a TTS message for sequential playback.
        :param text: The text to synthesize.
        :param user_number: Used to pick the OBS filter name.
        :param voice_name: Optional voice name (depends on your TTSManager).
        """
        job = {
            "text": text,
            "user_number": user_number,
            "voice_name": voice_name
        }
        self._queue.put(job)

    def reset(self) -> int:
        """
        Abandon all queued jobs (pending items) while letting the current
        in-flight job (if any) finish. Returns the number of jobs cleared.
        """
        cleared = 0
        while True:
            try:
                # Remove one pending job (if any)
                self._queue.get_nowait()
                # Each get() increments completion requirement by 1; we must
                # signal that this removed job is 'done' to keep the counter balanced.
                self._queue.task_done()
                cleared += 1
            except queue.Empty:
                break

        print(f"[VoiceManager] Queue reset: cleared {cleared} pending job(s).")
        return cleared
    # ------------- Internal worker -------------

    def _worker_loop(self):
        while not self._stop_event.is_set():
            try:
                # small timeout to avoid hot-spinning
                job = self._queue.get(timeout=0.05)
            except queue.Empty:
                continue

            try:
                text = job["text"]
                user_number = job["user_number"]
                voice_name = job["voice_name"]

                # 1) TTS synthesis
                try:
                    try:
                        tts_file = self.tts_manager.text_to_audio(text, voice_name)
                    except TypeError:
                        tts_file = self.tts_manager.text_to_audio(text)
                except Exception as e:
                    print(f"[VoiceManager] TTS error: {e}")
                    continue  # will hit 'finally' and task_done()

                # 2) OBS filter ON
                filter_name = f"Audio Move - Character {user_number}"
                try:
                    self.obswebsockets_manager.set_filter_visibility("Line In", filter_name, True)
                except Exception as e:
                    print(f"[VoiceManager] OBS on error: {e}")

                # 3) Play audio (blocking)
                try:
                    self.audio_manager.play_audio(tts_file, True, True, False)
                except Exception as e:
                    print(f"[VoiceManager] Error playing audio: {e}")
                finally:
                    # 4) OBS filter OFF
                    try:
                        self.obswebsockets_manager.set_filter_visibility("Line In", filter_name, False)
                    except Exception as e:
                        print(f"[VoiceManager] OBS off error: {e}")

            finally:
                # Exactly one task_done() for each get()
                self._queue.task_done()
                # tiny backoff if needed to avoid thrash in error loops
                # time.sleep(0.01)

    # ------------- Optional lifecycle helpers -------------

    def stop(self, drain: bool = False, timeout: float | None = None):
        """
        Stop the worker thread.
        :param drain: If True, finish remaining items before stopping.
        :param timeout: Optional join timeout in seconds.
        """
        if drain:
            try:
                self._queue.join()
            except Exception:
                pass
        self._stop_event.set()
        self._worker.join(timeout=timeout)