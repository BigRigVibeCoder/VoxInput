from unittest.mock import MagicMock

from src import pulseaudio_helper

FAKE_PACTL_OUTPUT = """
Source #1
    State: SUSPENDED
    Name: alsa_output.pci-0000_00_1f.3.analog-stereo.monitor
    Description: Monitor of Built-in Audio Analog Stereo
    Driver: module-alsa-card.c
    
Source #2
    State: SUSPENDED
    Name: alsa_input.pci-0000_00_1f.3.analog-stereo
    Description: Built-in Audio Analog Stereo
    Driver: module-alsa-card.c
    
Source #3
    State: RUNNING
    Name: rnnoise_source
    Description: Noise Cancelled Microphone
    Driver: module-null-sink.c
"""

def test_get_pulseaudio_sources(mocker):
    """Test parsing of pactl output."""
    mock_run = mocker.patch('subprocess.run')
    mock_run.return_value = MagicMock(
        stdout=FAKE_PACTL_OUTPUT,
        returncode=0
    )
    
    sources = pulseaudio_helper.get_pulseaudio_sources()
    
    assert len(sources) == 3
    assert sources[0].name == "alsa_output.pci-0000_00_1f.3.analog-stereo.monitor"
    assert sources[1].name == "alsa_input.pci-0000_00_1f.3.analog-stereo"
    assert sources[2].description == "Noise Cancelled Microphone"

def test_filter_input_sources():
    """Test filtering logic excludes monitors."""
    # Create fake device objects
    s1 = pulseaudio_helper.PulseAudioDevice("test.monitor", "Monitor of Speaker")
    s2 = pulseaudio_helper.PulseAudioDevice("mic.input", "Real Microphone")
    
    inputs = pulseaudio_helper.filter_input_sources([s1, s2])
    
    assert len(inputs) == 1
    assert inputs[0].name == "mic.input"
