import os
import sys
import uuid
import numpy as np

import sounddevice as sd
import soundfile as sf

from bark import generate_audio, preload_models

# ================= CONFIG =================

OUTPUT_DEVICE = "External Headphones" # "BlackHole 16ch"  # substring match
VOICE_PRESET = "v2/en_speaker_6"  # try 1–9 for variety
SAMPLE_RATE = 24000              # Bark output rate

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
TMP_DIR = os.path.join(SCRIPT_DIR, "tts_tmp")
os.makedirs(TMP_DIR, exist_ok=True)

# ================= INIT =================

print("Loading Bark models (first run takes a while)...")
preload_models()

print("Live Bark TTS → BlackHole")
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
            audio = generate_audio(
                text,
                history_prompt=VOICE_PRESET
            )

            # Ensure correct shape for sounddevice (Nx1)
            audio = np.asarray(audio, dtype=np.float32)
            audio = audio.reshape(-1, 1)

            # Save temp file (optional but keeps parity with your flow)
            sf.write(audio_path, audio, SAMPLE_RATE)

            # Play to selected device
            sd.play(audio, SAMPLE_RATE, device=OUTPUT_DEVICE)
            sd.wait()

        finally:
            if os.path.exists(audio_path):
                os.remove(audio_path)

except KeyboardInterrupt:
    print("\nExiting.")
    sys.exit(0)
