import pyaudio
import wave
import audioop
import sys

def diagnose():
    p = pyaudio.PyAudio()
    
    print("\n=== Audio Device Diagnostics ===")
    info = p.get_host_api_info_by_index(0)
    numdevices = info.get('deviceCount')
    
    # List all devices
    input_devices = []
    default_device_index = p.get_default_input_device_info()['index']
    
    print(f"Default Input Device Index: {default_device_index}")
    
    for i in range(0, numdevices):
        if (p.get_device_info_by_host_api_device_index(0, i).get('maxInputChannels')) > 0:
            name = p.get_device_info_by_host_api_device_index(0, i).get('name')
            print(f"Input Device id {i} - {name}")
            input_devices.append(i)

    print("\n=== Recording Test (5 seconds) ===")
    print("Please speak into the microphone...")
    
    CHUNK = 1024
    FORMAT = pyaudio.paInt16
    CHANNELS = 1
    RATE = 16000
    RECORD_SECONDS = 5
    
    try:
        stream = p.open(format=FORMAT,
                        channels=CHANNELS,
                        rate=RATE,
                        input=True,
                        frames_per_buffer=CHUNK)
    except Exception as e:
        print(f"CRITICAL: Failed to open default audio stream: {e}")
        return

    frames = []
    
    max_amplitude = 0
    
    for i in range(0, int(RATE / CHUNK * RECORD_SECONDS)):
        data = stream.read(CHUNK, exception_on_overflow=False)
        frames.append(data)
        
        # Check amplitude
        rms = audioop.rms(data, 2)
        if rms > max_amplitude:
            max_amplitude = rms
            
        # Visual meter
        meter = "#" * int((rms / 32768) * 50)
        sys.stdout.write(f"\rLevel: {rms:05d} [{meter:<50}]")
        sys.stdout.flush()

    print("\n\nRecording finished.")
    stream.stop_stream()
    stream.close()
    p.terminate()

    print(f"Peak Amplitude: {max_amplitude}")
    if max_amplitude < 100:
        print("\n[!] WARNING: Audio signal is extremely low or silent.")
        print("Possible causes:")
        print("1. Microphone hardware mute switch is on.")
        print("2. Wrong default input device selected in OS settings.")
        print("3. VM/Container input passthrough is missing.")
    elif max_amplitude < 500:
         print("\n[!] WARNING: Audio signal is very quiet.")
    else:
        print("\n[OK] Audio signal detected.")

    wf = wave.open("test_recording.wav", 'wb')
    wf.setnchannels(CHANNELS)
    wf.setsampwidth(p.get_sample_size(FORMAT))
    wf.setframerate(RATE)
    wf.writeframes(b''.join(frames))
    wf.close()
    print("Saved 'test_recording.wav'. Please play it back to verify quality.")

if __name__ == "__main__":
    diagnose()
