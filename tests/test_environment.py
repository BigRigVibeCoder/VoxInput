import unittest
import os
import sys
import importlib

class TestEnvironment(unittest.TestCase):
    def test_imports(self):
        """Test that all required modules can be imported."""
        modules = ['gi', 'vosk', 'pyaudio', 'pynput', 'src.main', 'src.audio', 'src.recognizer', 'src.config']
        for module in modules:
            with self.subTest(module=module):
                try:
                    importlib.import_module(module)
                except ImportError as e:
                    self.fail(f"Could not import {module}: {e}")

    def test_gi_bindings(self):
        """Test that Gtk and AppIndicator bindings are available."""
        try:
            import gi
            gi.require_version('Gtk', '3.0')
            gi.require_version('AppIndicator3', '0.1')
            from gi.repository import Gtk, AppIndicator3
        except ValueError as e:
             self.fail(f"GI Version requirement failed: {e}")
        except ImportError as e:
             self.fail(f"Could not import Gtk or AppIndicator3: {e}")

    def test_model_path_exists(self):
        """Test that the Vosk model path matches config and exists."""
        from src.config import MODEL_PATH
        self.assertTrue(os.path.exists(MODEL_PATH), f"Model path does not exist: {MODEL_PATH}")
        self.assertTrue(os.path.isdir(MODEL_PATH), f"Model path is not a directory: {MODEL_PATH}")

    def test_log_file_creation(self):
        """Test that the log file can be created/written to."""
        from src.config import LOG_FILE
        try:
            with open(LOG_FILE, 'a') as f:
                pass
        except IOError as e:
            self.fail(f"Could not write to log file {LOG_FILE}: {e}")

if __name__ == '__main__':
    unittest.main()
