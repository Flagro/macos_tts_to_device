import os
import sys
import uuid
import threading
import numpy as np

import sounddevice as sd
import soundfile as sf

from bark import generate_audio, preload_models

# ================= CONFIG =================

# Multiple output devices - can be device names (substring match) or device IDs
OUTPUT_DEVICES = [
    "External Headphones"
]  # Add more devices: ["BlackHole 16ch", "External Headphones"]
VOICE_PRESET = "v2/en_speaker_6"  # try 1–9 for variety
SAMPLE_RATE = 24000  # Bark output rate

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
TMP_DIR = os.path.join(SCRIPT_DIR, "tts_tmp")
os.makedirs(TMP_DIR, exist_ok=True)

# ================= INIT =================

print("Loading Bark models (first run takes a while)...")
preload_models()

print("Live Bark TTS → Multiple Devices")
print(f"Output devices: {OUTPUT_DEVICES}")
print(f"Temp files: {TMP_DIR}")
print(f"Voice preset: {VOICE_PRESET}")
print("Type a line and press Enter (Ctrl+C to quit)\n")

# ================= LOOP =================

try:
    while True:
        text = input("> ").strip()
        if not text:
            continue

        audio_path = os.path.join(TMP_DIR, f"{uuid.uuid4().hex}.wav")

        try:
            # Generate Bark audio (float32 numpy array)
            audio = generate_audio(text, history_prompt=VOICE_PRESET)

            # Ensure correct shape for sounddevice (Nx1)
            audio = np.asarray(audio, dtype=np.float32)
            audio = audio.reshape(-1, 1)

            # Save temp file (optional but keeps parity with your flow)
            sf.write(audio_path, audio, SAMPLE_RATE)

            # Play to all selected devices simultaneously
            def play_on_device(device_name):
                """Play audio on a specific device"""
                try:
                    sd.play(audio, SAMPLE_RATE, device=device_name)
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
