import os

# Paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH = os.path.join(BASE_DIR, "..", "model")

# Audio Settings
SAMPLE_RATE = 16000
CHANNELS = 1
CHUNK_SIZE = 1600  # 100ms @ 16kHz — optimal for real-time feel (P1-01)
                   # Was 8000 (500ms). Reduced 5x for sub-150ms perceived latency.
                   # Compromise: use 3200 (200ms) if CPU spikes on slow hardware.

# Hotkey
HOTKEY = '<cmd>+<shift>+v'  # Super+Shift+V

# Logging
LOG_FILE = os.path.join(BASE_DIR, "..", "voxinput.log")
