from pynput.keyboard import Controller, Key

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
            
        self.keyboard.type(text + ' ')

    def backspace(self):
        self.keyboard.press(Key.backspace)
        self.keyboard.release(Key.backspace)
