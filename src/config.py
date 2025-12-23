import os

# Paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH = os.path.join(BASE_DIR, "..", "model")

# Audio Settings
SAMPLE_RATE = 16000
CHANNELS = 1
CHUNK_SIZE = 8000

# Hotkey
HOTKEY = '<cmd>+<shift>+v'  # Super+Shift+V

# Logging
LOG_FILE = os.path.join(BASE_DIR, "..", "voxinput.log")
