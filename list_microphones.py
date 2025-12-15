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

    print("\nTo set a specific microphone:")
    print("1. Open 'src/config.py'")
    print("2. Set INPUT_DEVICE_INDEX = <id_number> (e.g. INPUT_DEVICE_INDEX = 2)")
    print("3. Restart the application.")
    
    p.terminate()

if __name__ == "__main__":
    diagnose()
