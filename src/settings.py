
import json
import logging
import os

logger = logging.getLogger(__name__)

SETTINGS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "settings.json")

class SettingsManager:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(SettingsManager, cls).__new__(cls)
            cls._instance.settings = {}
            cls._instance.load()
        return cls._instance

    def load(self):
        if os.path.exists(SETTINGS_FILE):
            try:
                with open(SETTINGS_FILE, 'r') as f:
                    self.settings = json.load(f)
                logger.info("Settings loaded successfully")
            except Exception as e:
                logger.error(f"Failed to load settings: {e}")
                self.settings = {}
        else:
            self.settings = {}

    def save(self):
        try:
            with open(SETTINGS_FILE, 'w') as f:
                json.dump(self.settings, f, indent=4)
            logger.info("Settings saved successfully")
        except Exception as e:
            logger.error(f"Failed to save settings: {e}")

    def get(self, key, default=None):
        if key == "whisper_model_size" and default is None:
            default = "small"
        return self.settings.get(key, default)

    def set(self, key, value):
        self.settings[key] = value
        self.save()

    @classmethod
    def reset(cls):
        """Reset singleton instance. Used in tests to prevent state pollution. (P0-05)"""
        cls._instance = None
