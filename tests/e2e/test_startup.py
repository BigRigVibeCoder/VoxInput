
# Ensure mocks are in place before importing app
# conftest.py handles gi/pyaudio/vosk at module level.
# pynput is not installed in the test venv — mock it here too.
import sys
from unittest.mock import MagicMock

# Mock pynput before any src imports attempt it
if "pynput" not in sys.modules:
    sys.modules["pynput"] = MagicMock()
    sys.modules["pynput.keyboard"] = MagicMock()

def test_app_initialization(monkeypatch, mock_settings_file):
    """
    E2E-ish test: Initialize the main app class with all dependencies mocked.
    Verifies start/stop listening state machine works correctly.
    """
    # Patch SettingsManager to return predictable values
    mock_sm = MagicMock()

    def mock_get(key, default=None):
        if key == "vosk_model_path": return "/mock/model/path"
        return default

    mock_sm.return_value.get.side_effect = mock_get
    monkeypatch.setattr("src.settings.SettingsManager", mock_sm)

    # Import and instantiate with all heavy deps already mocked by conftest + above
    from src.main import VoxInputApp
    app = VoxInputApp()

    # Verify critical components initialized
    assert app.audio is not None

    # Wait for background model loader thread to finish
    import time
    for _ in range(50):
        if app.recognizer is not None:
            break
        time.sleep(0.1)

    assert app.recognizer is not None
    assert app.ui is not None
    assert app.is_listening is False

    # Verify start/stop state machine
    app.start_listening()
    assert app.is_listening is True
    assert app.processing_thread is not None

    app.stop_listening()
    assert app.is_listening is False
    assert app.processing_thread is None
