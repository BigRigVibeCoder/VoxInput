import logging
import subprocess

from pynput.keyboard import Controller, Key

logger = logging.getLogger(__name__)

class TextInjector:
    def __init__(self):
        self.keyboard = Controller()

    def type_text(self, text):
        """
        Types the text at the current cursor position.
        Adds a space at the end for continuity.
        """
        # Clean text if needed
        text = text.strip()
        if not text:
            return
            
        full_text = text + ' '
        logger.info(f"Injecting text: '{full_text}'")

        # Try xdotool first (Better for Linux)
        try:
            # --clearmodifiers prevents stuck keys (like Control/Alt) from interfering
            # --delay 0 speeds it up
            subprocess.run(['xdotool', 'type', '--clearmodifiers', '--delay', '0', full_text], check=True)
            return
        except (subprocess.CalledProcessError, FileNotFoundError):
            logger.warning("xdotool failed or not found, falling back to pynput")
        
        # Fallback to pynput
        try:
            self.keyboard.type(full_text)
        except Exception as e:
             logger.error(f"Text injection failed: {e}")

    def backspace(self):
        try:
            subprocess.run(['xdotool', 'key', 'BackSpace'], check=True)
            return
        except Exception:
            pass
            
        self.keyboard.press(Key.backspace)
        self.keyboard.release(Key.backspace)
