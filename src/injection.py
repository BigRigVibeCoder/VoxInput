from pynput.keyboard import Controller, Key
import logging
import subprocess
import shutil

logger = logging.getLogger(__name__)

class TextInjector:
    def __init__(self):
        self.keyboard = Controller()
        self.has_xdotool = shutil.which('xdotool') is not None
        if self.has_xdotool:
            logger.info("xdotool detected. Will use as primary injection method (more reliable).")
        else:
            logger.warning("xdotool not found. Using pynput (might fail on some windows).")

    def type_text(self, text):
        """
        Types the text at the current cursor position.
        Adds a space at the end for continuity.
        """
        # Clean text if needed
        text = text.strip()
        if not text:
            return
            
        logger.info(f"Injecting text: '{text}'")
        
        # Method 1: xdotool (Best for X11)
        if self.has_xdotool:
            try:
                # Use --clearmodifiers to ensure shift/ctrl state doesn't mess up typing
                subprocess.run(['xdotool', 'type', '--clearmodifiers', text + ' '], check=False)
                return
            except Exception as e:
                logger.error(f"xdotool failed: {e}")

        # Method 2: pynput (Fallback)
        try:
            self.keyboard.type(text + ' ')
        except Exception as e:
             logger.error(f"pynput failed: {e}")

    def backspace(self):
        self.keyboard.press(Key.backspace)
        self.keyboard.release(Key.backspace)
