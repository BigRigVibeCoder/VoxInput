import signal
import sys
import threading
import time
import logging
import json
import os
from .config import HOTKEY, LOG_FILE, SETTINGS_FILE, DEFAULT_ENGINE

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
        
        # Load Settings Early for persistence
        settings = self.load_settings()
        saved_engine = settings.get('recognition_engine', DEFAULT_ENGINE)
        saved_index = settings.get('input_device_index')
        
        # Initialize Recognizer with saved engine
        self.recognizer = SpeechRecognizer(engine_type=saved_engine)
        self.injector = TextInjector()
        
        self.is_listening = False
        self.should_quit = False
        self.processing_thread = None
        self.current_partial_text = "" # Track actual text content for diffing
        
        # Audio Device Persistence
        if saved_index is not None:
             logger.info(f"Loaded persisted audio device index: {saved_index}")
             self.audio.set_device_index(saved_index)
        
        # Get Input Devices
        devices = self._get_input_devices()

        # Initialize UI
        self.ui = SystemTrayApp(
            toggle_callback=self.toggle_listening,
            quit_callback=self.quit_app,
            input_devices=devices,
            on_device_changed=self.change_input_device,
            current_device_index=saved_index,
            on_engine_changed=self.change_recognition_engine,
            current_engine=saved_engine
        )

    def _get_input_devices(self):
        """Returns list of (index, name) tuples."""
        try:
            p = self.audio.pa
            info = p.get_host_api_info_by_index(0)
            numdevices = info.get('deviceCount')
            devices = []
            
            # Keywords to exclude (Raw hardware/output paths that aren't mics)
            excluded_keywords = [
                'surround', 'rear', 'center', 'lfe', 'side', 'iec958', 'hdmi', 'dmix', 
                'dsnoop', 'loopback', 'monitor'
            ]
            
            for i in range(0, numdevices):
                dev_info = p.get_device_info_by_host_api_device_index(0, i)
                if dev_info.get('maxInputChannels') > 0:
                    name = dev_info.get('name')
                    lower_name = name.lower()
                    
                    # Filter out excluded stuff
                    if any(k in lower_name for k in excluded_keywords):
                        continue

                    # Rename likely system defaults to be friendlier
                    if name == 'pulse':
                        name = "System Default (Follows OS Settings)"
                    elif name == 'default':
                        name = "ALSA Default"
                    
                    devices.append((i, name))
            
            # Sort devices: Put 'System Default' first
            devices.sort(key=lambda x: 0 if "Follows OS Settings" in x[1] else 1)
            return devices
        except Exception as e:
            logger.error(f"Error listing devices: {e}")
            return []

    def load_settings(self):
        try:
            if os.path.exists(SETTINGS_FILE):
                with open(SETTINGS_FILE, 'r') as f:
                    return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load settings: {e}")
        return {}

    def save_settings(self, data):
        try:
            settings = self.load_settings()
            settings.update(data)
            with open(SETTINGS_FILE, 'w') as f:
                json.dump(settings, f)
        except Exception as e:
             logger.error(f"Failed to save settings: {e}")

    def change_input_device(self, index):
        logger.info(f"Changing input device to Index: {index}")
        
        # Save persistence
        self.save_settings({'input_device_index': index})

        was_listening = self.is_listening
        
        if was_listening:
            self.stop_listening()
            
        self.audio.set_device_index(index)
        
        if was_listening:
            self.start_listening()

    def change_recognition_engine(self, engine_id):
        logger.info(f"Changing recognition engine to: {engine_id}")
        
        # Save persistence
        self.save_settings({'recognition_engine': engine_id})
        
        # Switch Engine (Hot swap possible? Yes, but cleaner to pause)
        was_listening = self.is_listening
        if was_listening:
            self.stop_listening()
            
        self.recognizer.set_engine(engine_id)
        
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
        self.current_partial_text = "" # Reset
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
                    text, is_final = self.recognizer.process_audio(data)
                    if text:
                        # Logic:
                        # 1. Calculate Diff against current_partial_text
                        # 2. Update screen (Delete + Type)
                        # 3. Update current_partial_text state
                        # 4. If Final, CLEAR current_partial_text state
                        
                        # Early exit optimization for identical text (prevents redundant typing/space deletion)
                        if text == self.current_partial_text:
                            if is_final:
                                self.current_partial_text = "" # Ensure reset!
                            continue
                        
                        # Calculate Common Prefix
                        common_len = 0
                        if self.current_partial_text:
                            min_len = min(len(self.current_partial_text), len(text))
                            for i in range(min_len):
                                if self.current_partial_text[i] == text[i]:
                                    common_len += 1
                                else:
                                    break
                        
                        # Calculate Deletion
                        chars_to_delete = 0
                        if self.current_partial_text:
                            remaining_len = len(self.current_partial_text) - common_len
                            if remaining_len > 0:
                                # Divergence: Delete everything after common prefix + trailing space
                                chars_to_delete = remaining_len + 1 
                            else:
                                # Prefix Match: Just delete trailing space to append
                                chars_to_delete = 1 

                        if chars_to_delete > 0:
                            self.injector.delete_chars(chars_to_delete)
                            
                        # Calculate Addition
                        text_to_type = text[common_len:]
                        
                        # Type Suffix
                        # add_space=True ensures word separation
                        self.injector.type_text(text_to_type, add_space=True)
                        
                        # State Update
                        if is_final:
                            self.current_partial_text = ""
                        else:
                            self.current_partial_text = text 
                            
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
