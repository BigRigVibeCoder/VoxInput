import logging
import logging.handlers
import queue as _queue
import signal
import sys
import threading
import time

from gi.repository import GLib
from pynput import keyboard

from .audio import AudioCapture
from .config import HOTKEY, LOG_FILE
from .injection import TextInjector
from .mic_enhancer import MicEnhancer       # P6: Ubuntu mic signal enhancement
from .recognizer import SpeechRecognizer
from .settings import SettingsManager
from .spell_corrector import SpellCorrector  # P3: SymSpellPy ASR correction

# Imports moved to top level compliant with PEP8 (requires careful circular dep check)
# In this simple app, these depend only on standard libs or other simple modules
from .ui import Gtk, SystemTrayApp

# Configure Logging — rotating 5MB × 3 files (P0-03)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.handlers.RotatingFileHandler(
            LOG_FILE, maxBytes=5_000_000, backupCount=3
        ),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


class VoxInputApp:
    def __init__(self):
        self.audio = AudioCapture()
        self.recognizer = SpeechRecognizer()
        self.injector = TextInjector()
        self.settings = SettingsManager()
        self.spell = SpellCorrector(self.settings)     # P3: corrects before injection
        self.mic = MicEnhancer(self.settings)          # P6: Ubuntu mic controls
        self.mic.restore_settings()                    # re-apply saved vol/noise/boost

        self.is_listening = False
        self.should_quit = False
        self.processing_thread = None

        # P0-04 / P1-04: Dedicated injection thread — decouples xdotool latency
        # from the audio processing loop so recognition never stalls on typing.
        self._injection_queue: _queue.Queue = _queue.Queue(maxsize=100)
        self._injection_thread = threading.Thread(
            target=self._injection_loop, daemon=True, name="injection"
        )
        self._injection_thread.start()

        # Initialize UI
        self.ui = SystemTrayApp(
            toggle_callback=self.toggle_listening,
            quit_callback=self.quit_app,
            engine_change_callback=self.reload_engine
        )

    def reload_engine(self):
        logger.info("Reloading speech engine...")
        was_listening = self.is_listening
        if was_listening:
            self.stop_listening()
            
        try:
            # Re-initialize recognizer (reads new settings)
            self.recognizer = SpeechRecognizer()
            logger.info("Engine reloaded successfully.")
        except Exception as e:
            logger.error(f"Failed to reload engine: {e}")
            return

        if was_listening:
            self.start_listening()

    def toggle_listening(self):
        if self.is_listening:
            self.stop_listening()
        else:
            self.start_listening()

    def start_listening(self):
        if self.is_listening:
            logger.warning("Already listening.")
            return
            
        logger.info("Starting listening...")
        self.is_listening = True
        self.ui.set_listening_state(True)
        self.recognizer.reset_state() # Reset streaming buffers
        self.audio.start()
        
        self.processing_thread = threading.Thread(target=self._process_loop)
        self.processing_thread.start()

    def stop_listening(self):
        if not self.is_listening:
            return

        logger.info("Stopping listening...")
        self.is_listening = False
        self.ui.set_listening_state(False)
        self.ui.update_osd("", 0.0)   # P5: clear OSD on stop
        self.audio.stop()

        if self.processing_thread:
            # P0-04: 8s timeout — must outlast worst-case CPU Whisper inference
            self.processing_thread.join(timeout=8.0)
            if self.processing_thread.is_alive():
                logger.warning("Processing thread did not exit cleanly within 8s")
            self.processing_thread = None

    def _injection_loop(self):
        """Dedicated thread: drains injection queue → xdotool. (P1-04)"""
        while not self.should_quit:
            try:
                text = self._injection_queue.get(timeout=0.1)
                self.injector.type_text(text)
            except _queue.Empty:
                continue
            except Exception as e:
                logger.error(f"Injection error: {e}")

    def _process_loop(self):
        import numpy as np  # numpy always present (P0-01)

        silence_start_time = None
        osd_words: list[str] = []   # P5: accumulate words for OSD display

        while self.is_listening and not self.should_quit:
            data = self.audio.get_data()
            if data:
                # --- Silence Detection (P0-01: numpy RMS replaces audioop) ---
                try:
                    audio_np = np.frombuffer(data, dtype=np.int16)
                    rms = int(np.sqrt(np.mean(audio_np.astype(np.float64) ** 2)))
                except Exception:
                    rms = 0

                # P5: feed live level to OSD (normalised 0–1)
                level = min(rms / 8000.0, 1.0)
                self.ui.update_osd(" ".join(osd_words[-8:]), level)

                if rms < self.settings.get("silence_threshold", 500):
                    if silence_start_time is None:
                        silence_start_time = time.time()
                    elif time.time() - silence_start_time > self.settings.get("silence_duration", 0.6):
                        try:
                            final_text = self.recognizer.finalize()
                            if final_text:
                                logger.info(f"Finalized (Silence): {final_text}")
                                self._enqueue_injection(final_text)
                                osd_words.clear()          # reset OSD accumulator
                        except Exception as e:
                            logger.error(f"Error finalizing: {e}")
                        silence_start_time = None
                else:
                    silence_start_time = None

                # --- Normal Processing ---
                try:
                    text = self.recognizer.process_audio(data)
                    if text:
                        logger.info(f"Recognized: {text}")
                        self._enqueue_injection(text)
                        osd_words.extend(text.split())   # P5: accumulate for OSD
                except Exception as e:
                    logger.error(f"Error processing audio: {e}", exc_info=True)
            else:
                time.sleep(0.01)

    def _enqueue_injection(self, text: str):
        """Spell-correct then push to injection queue (non-blocking). (P3)"""
        try:
            corrected = self.spell.correct(text)  # P3: SymSpellPy + ASR rules
            self._injection_queue.put_nowait(corrected)
        except _queue.Full:
            logger.warning("Injection queue full — dropping word batch (engine too slow?)")

    def quit_app(self):
        self.should_quit = True
        self.stop_listening()
        self.audio.terminate()
        Gtk.main_quit()
        sys.exit(0)

    def run(self):
        # Setup signal handlers
        signal.signal(signal.SIGINT, lambda s, f: self.quit_app())
        signal.signal(signal.SIGUSR1, lambda s, f: self.toggle_listening())
        
        # Start global hotkey listener
        # Note: Global hotkeys with pynput on Linux can be tricky and might block.
        # We are now using system-level shortcuts via SIGUSR1, so we disable this internal listener
        # to prevent double-triggering (System Shortcut + Internal Pynput).
        # self.hotkey_thread = threading.Thread(target=self._listen_hotkeys)
        # self.hotkey_thread.daemon = True
        # self.hotkey_thread.start()
        
        # Run UI loop
        Gtk.main()

    def _listen_hotkeys(self):
        
        def on_activate():
            # Run in main thread context if possible, or careful with Gtk
            # Gtk is not thread safe. Use GLib.idle_add
            GLib.idle_add(self.toggle_listening)

        # Parse hotkey string or hardcode for now
        # simple wrapper
        with keyboard.GlobalHotKeys({
            HOTKEY: on_activate
        }) as h:
            h.join()

if __name__ == "__main__":
    try:
        app = VoxInputApp()
        logger.info("VoxInput Application Started")
        app.run()
    except Exception as e:
        logger.critical(f"Unhandled exception in main: {e}", exc_info=True)
        sys.exit(1)
