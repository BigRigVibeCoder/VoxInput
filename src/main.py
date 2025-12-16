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
        
        self.is_listening = False
        self.should_quit = False
        self.processing_thread = None
        
        # Initialize UI
        self.ui = SystemTrayApp(
            toggle_callback=self.toggle_listening,
            quit_callback=self.quit_app
        )

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
        while self.is_listening and not self.should_quit:
            data = self.audio.get_data()
            if data:
                try:
                    text = self.recognizer.process_audio(data)
                    if text:
                        logger.info(f"Recognized: {text}")
                        # Inject text to main thread or via UI idle add if needed?
                        # pynput is thread safe mostly, but let's be careful.
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
        
        # Start global hotkey listener
        # Note: Global hotkeys with pynput on Linux can be tricky and might block.
        # Running it in a separate thread.
        self.hotkey_thread = threading.Thread(target=self._listen_hotkeys)
        self.hotkey_thread.daemon = True
        self.hotkey_thread.start()
        
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
