import os

# Paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH = os.path.join(BASE_DIR, "..", "model")

# Audio Settings
SAMPLE_RATE = 16000
CHANNELS = 1
CHUNK_SIZE = 8000
INPUT_DEVICE_INDEX = None  # None = System Default. Set to integer index (e.g., 1, 2) to force specific device.

# Hotkey
HOTKEY = '<ctrl>+<alt>+m'  # Ctrl+Alt+M

# Engines
# Options: "vosk", "whisper"
DEFAULT_ENGINE = "vosk"
# Whisper options: "tiny", "base", "small", "medium", "large"
# "base" is a good balance of speed/accuracy for CPU.
WHISPER_MODEL_SIZE = "base"

# Logging
LOG_FILE = os.path.join(BASE_DIR, "..", "voxinput.log")
SETTINGS_FILE = os.path.join(BASE_DIR, "..", "settings.json")
