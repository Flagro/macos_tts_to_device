"""Bark AI TTS engine implementation."""

import numpy as np
import soundfile as sf
from typing import Tuple

from .tts_base import TTSEngine


class BarkTTSEngine(TTSEngine):
    """TTS engine using Suno's Bark AI model."""

    def __init__(
        self,
        output_devices: list,
        voice_preset: str = "v2/en_speaker_6",
        sample_rate: int = 24000,
        tmp_dir: str = None,
    ):
        """
        Initialize the Bark TTS engine.

        Args:
            output_devices: List of output device names or IDs
            voice_preset: Bark voice preset (e.g., "v2/en_speaker_6")
            sample_rate: Sample rate for audio output (default: 24000)
            tmp_dir: Directory for temporary audio files
        """
        super().__init__(output_devices, tmp_dir)
        self.voice_preset = voice_preset
        self.sample_rate = sample_rate

        # Lazy import to avoid loading Bark if not needed
        from bark import preload_models

        print("Loading Bark models (first run takes a while)...")
        preload_models()

    def generate_audio(self, text: str) -> Tuple[str, int]:
        """
        Generate audio using Bark AI.

        Args:
            text: Text to convert to speech

        Returns:
            Tuple of (audio_file_path, sample_rate)
        """
        from bark import generate_audio

        audio_path = self.generate_temp_path("wav")

        # Generate Bark audio (float32 numpy array)
        audio = generate_audio(text, history_prompt=self.voice_preset)

        # Ensure correct shape for soundfile (Nx1)
        audio = np.asarray(audio, dtype=np.float32)
        audio = audio.reshape(-1, 1)

        # Save to file
        sf.write(audio_path, audio, self.sample_rate)

        return audio_path, self.sample_rate

    def get_engine_name(self) -> str:
        """Return the name of the TTS engine."""
        return "Live Bark TTS"

    def _print_engine_specific_info(self):
        """Print Bark-specific configuration info."""
        print(f"Voice preset: {self.voice_preset}")
        print(f"Sample rate: {self.sample_rate} Hz")
