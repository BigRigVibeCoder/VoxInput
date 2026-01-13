import sys
from unittest.mock import MagicMock

import pytest

# Mock pyaudio and vosk modules BEFORE they are imported by app code
# This prevents "ModuleNotFoundError" or hardware initialization errors during tests
sys.modules["pyaudio"] = MagicMock()
sys.modules["vosk"] = MagicMock()
sys.modules["gi"] = MagicMock()
sys.modules["gi.repository"] = MagicMock()
sys.modules["gi.repository.Gtk"] = MagicMock()
sys.modules["gi.repository.Gdk"] = MagicMock()
sys.modules["gi.repository.GLib"] = MagicMock()
sys.modules["gi.repository.AppIndicator3"] = MagicMock()

@pytest.fixture
def mock_pyaudio():
    """Returns the mocked pyaudio module."""
    return sys.modules["pyaudio"]

@pytest.fixture
def mock_vosk():
    """Returns the mocked vosk module."""
    return sys.modules["vosk"]

@pytest.fixture
def mock_settings_file(tmp_path):
    """Creates a temporary settings.json file."""
    settings_file = tmp_path / "settings.json"
    settings_file.write_text('{"engine": "vosk", "vosk_model_path": "/tmp/fake/model"}')
    return str(settings_file)
