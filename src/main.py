import signal
import sys
import threading
import time
import logging
from .config import HOTKEY, LOG_FILE

# Configure Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

try:
    from .ui import SystemTrayApp, Gtk
except ImportError as e:
    import traceback
    logger.critical(f"Could not import UI modules: {e}")
    traceback.print_exc()
    sys.exit(1)

from .audio import AudioCapture
from .recognizer import SpeechRecognizer
from .injection import TextInjector

class VoxInputApp:
    def __init__(self):
        self.audio = AudioCapture()
        self.recognizer = SpeechRecognizer()
        self.injector = TextInjector()
        
        from .settings import SettingsManager
        self.settings = SettingsManager()
        
        self.is_listening = False
        self.should_quit = False
        self.processing_thread = None
        
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
        self.audio.stop()
        
        if self.processing_thread:
            self.processing_thread.join(timeout=1.0)
            self.processing_thread = None

    def _process_loop(self):
        import audioop
        
        silence_start_time = None
        # Defaults
        SILENCE_THRESHOLD_RMS = self.settings.get("silence_threshold", 500)
        SILENCE_DURATION_SEC = self.settings.get("silence_duration", 0.6)
        
        while self.is_listening and not self.should_quit:
            data = self.audio.get_data()
            if data:
                # --- Silence Detection ---
                try:
                    rms = audioop.rms(data, 2) # 2 bytes per sample (16-bit)
                except Exception:
                    rms = 0
                
                if rms < self.settings.get("silence_threshold", 500):
                    if silence_start_time is None:
                        silence_start_time = time.time()
                    elif time.time() - silence_start_time > self.settings.get("silence_duration", 0.6):
                        # User has stopped speaking for > duration
                        # Check if we need to finalize (force flush) any pending Whisper buffer
                        try:
                            final_text = self.recognizer.finalize()
                            if final_text:
                                logger.info(f"Finalized (Silence): {final_text}")
                                self.injector.type_text(final_text)
                        except Exception as e:
                            logger.error(f"Error finalizing: {e}")
                        
                        silence_start_time = None # Reset so we don't spam finalize
                else:
                    # Voice detected
                    silence_start_time = None

                # --- Normal Processing ---
                try:
                    text = self.recognizer.process_audio(data)
                    if text:
                        logger.info(f"Recognized: {text}")
                        self.injector.type_text(text)
                except Exception as e:
                    logger.error(f"Error processing audio: {e}", exc_info=True)
            else:
                time.sleep(0.01)

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
        from pynput import keyboard
        
        def on_activate():
            # Run in main thread context if possible, or careful with Gtk
            # Gtk is not thread safe. Use GLib.idle_add
            from gi.repository import GLib
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
