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

    def type_text(self, text, add_space=True):
        """
        Types the text at the current cursor position.
        add_space: If True, appends a space at the end.
        """
        if not text:
            return
            
        # logger.info(f"Injecting text: '{text}'")
        
        final_text = text + (' ' if add_space else '')

        # Method 1: xdotool (Best for X11)
        if self.has_xdotool:
            try:
                # Use --clearmodifiers to ensure shift/ctrl state doesn't mess up typing
                # Note: xdotool might strip leading spaces in some contexts or arguments?
                # Using single quotes for safety in logger, but subprocess passes args directly.
                # Delay 2ms to prevent dropped keys on high load
                subprocess.run(['xdotool', 'type', '--clearmodifiers', '--delay', '2', final_text], check=False)
                return
            except Exception as e:
                logger.error(f"xdotool failed: {e}")

        # Method 2: pynput (Fallback)
        try:
            self.keyboard.type(final_text)
        except Exception as e:
             logger.error(f"pynput failed: {e}")

    def backspace(self):
        self.keyboard.press(Key.backspace)
        self.keyboard.release(Key.backspace)

    def delete_chars(self, count):
        if count <= 0:
            return
        
        # Method 1: xdotool key repeat
        if self.has_xdotool:
            try:
                # 'BackSpace' is the key name for xdotool
                subprocess.run(['xdotool', 'key', '--clearmodifiers', '--repeat', str(count), 'BackSpace'], check=False)
                return
            except Exception as e:
                logger.error(f"xdotool backspace failed: {e}")

        # Method 2: pynput loop
        for _ in range(count):
            self.backspace()
