
# Ensure mocks are in place before importing app
# (conftest.py handles module-level mocks, but we verify here)

def test_app_initialization(mocker, mock_settings_file):
    """
    E2E-ish test: Initialize the main app class.
    We mock out:
    - AudioCapture (pyaudio dependencies)
    - SpeechRecognizer (vosk/torch dependencies)
    - SettingsManager (filesystem)
    - SystemTrayApp (GTK)
    """
    
    # 1. Patch internal classes used by VoxInputApp
    mocker.patch('src.audio.AudioCapture')
    mocker.patch('src.recognizer.SpeechRecognizer')
    mocker.patch('src.injection.TextInjector')
    mocker.patch('src.ui.SystemTrayApp')
    
    # 2. Patch SettingsManager to load our temp file
    # We mock the entire class for simplicity in this E2E test
    mock_settings = mocker.patch('src.settings.SettingsManager')
    mock_settings.return_value.get.return_value = 500 # Default return for any get()
    
    # 3. Import and Instantiate
    from src.main import VoxInputApp
    app = VoxInputApp()
    
    # 4. Verify critical components were initialized
    assert app.audio is not None
    assert app.recognizer is not None
    assert app.ui is not None
    assert app.is_listening is False
    
    # 5. Verify start/stop logic (state machine)
    app.start_listening()
    assert app.is_listening is True
    # Verify processing thread started
    assert app.processing_thread is not None
    
    app.stop_listening()
    assert app.is_listening is False
    assert app.processing_thread is None
