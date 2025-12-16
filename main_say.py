import os
import sys
import uuid
import subprocess

import sounddevice as sd
import soundfile as sf

OUTPUT_DEVICE = "BlackHole 16ch"  # substring match is supported
VOICE = None  # e.g. "Alex", or None

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
TMP_DIR = os.path.join(SCRIPT_DIR, "tts_tmp")
os.makedirs(TMP_DIR, exist_ok=True)

print("Live TTS → BlackHole")
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

            # Play to selected device
            data, samplerate = sf.read(audio_path, dtype="float32", always_2d=True)
            sd.play(data, samplerate, device=OUTPUT_DEVICE)
            sd.wait()

        finally:
            if os.path.exists(audio_path):
                os.remove(audio_path)

except KeyboardInterrupt:
    print("\nExiting.")
    sys.exit(0)
