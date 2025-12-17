import os
import sys
import uuid
import subprocess
import threading

import sounddevice as sd
import soundfile as sf

# Multiple output devices - can be device names (substring match) or device IDs
OUTPUT_DEVICES = [
    "BlackHole 16ch"
]  # Add more devices: ["BlackHole 16ch", "External Headphones"]
VOICE = None  # e.g. "Alex", or None

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
TMP_DIR = os.path.join(SCRIPT_DIR, "tts_tmp")
os.makedirs(TMP_DIR, exist_ok=True)

print("Live TTS → Multiple Devices")
print(f"Output devices: {OUTPUT_DEVICES}")
print(f"Temp files: {TMP_DIR}")
print("Type a line and press Enter (Ctrl+C to quit)\n")

try:
    while True:
        text = input("> ").strip()
        if not text:
            continue

        audio_path = os.path.join(TMP_DIR, f"{uuid.uuid4().hex}.aiff")

        try:
            # Generate TTS
            cmd = ["say"]
            if VOICE:
                cmd += ["-v", VOICE]
            cmd += [text, "-o", audio_path]
            subprocess.run(cmd, check=True)

            # Play to all selected devices simultaneously
            data, samplerate = sf.read(audio_path, dtype="float32", always_2d=True)

            def play_on_device(device_name):
                """Play audio on a specific device"""
                try:
                    sd.play(data, samplerate, device=device_name)
                    sd.wait()
                except Exception as e:
                    print(f"Error playing on device '{device_name}': {e}")

            # Start playback on all devices in parallel
            threads = []
            for device in OUTPUT_DEVICES:
                thread = threading.Thread(target=play_on_device, args=(device,))
                thread.start()
                threads.append(thread)

            # Wait for all devices to finish playing
            for thread in threads:
                thread.join()

        finally:
            if os.path.exists(audio_path):
                os.remove(audio_path)

except KeyboardInterrupt:
    print("\nExiting.")
    sys.exit(0)
