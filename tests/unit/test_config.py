import os

from src import config


def test_paths_exist():
    """Verify that critical paths are defined."""
    assert os.path.isabs(config.BASE_DIR)
    assert config.MODEL_PATH.endswith("model")

def test_audio_settings():
    """Verify default audio settings are sane."""
    assert config.SAMPLE_RATE == 16000
    assert config.CHANNELS == 1
    assert config.CHUNK_SIZE > 0

def test_hotkey_format():
    """Verify hotkey is a valid string."""
    assert isinstance(config.HOTKEY, str)
    assert "+" in config.HOTKEY
