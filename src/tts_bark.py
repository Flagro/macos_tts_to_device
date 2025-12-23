"""Bark AI TTS engine implementation."""

import logging
import numpy as np
import soundfile as sf
from typing import Tuple, List

from .tts_base import TTSEngine

logger = logging.getLogger(__name__)


class BarkTTSEngine(TTSEngine):
    """TTS engine using Suno's Bark AI model."""

    def __init__(
        self,
        output_devices: List[str],
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

        logger.info(
            f"Initialized BarkTTSEngine with voice_preset='{voice_preset}', "
            f"sample_rate={sample_rate}, devices={output_devices}"
        )

        # Lazy import to avoid loading Bark if not needed
        try:
            from bark import preload_models

            print("Loading Bark models (first run takes a while)...")
            logger.info("Starting Bark model loading...")
            preload_models()
            logger.info("Bark models loaded successfully")
        except ImportError as e:
            logger.error(f"Failed to import Bark: {e}")
            raise
        except Exception as e:
            logger.error(f"Failed to load Bark models: {e}", exc_info=True)
            raise RuntimeError(f"Failed to load Bark models: {e}") from e

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

        logger.debug(f"Generating Bark audio with preset '{self.voice_preset}'")
        
        try:
            # Generate Bark audio (float32 numpy array)
            audio = generate_audio(text, history_prompt=self.voice_preset)
            logger.info(f"Bark audio generation completed")

            # Ensure correct shape for soundfile (Nx1)
            audio = np.asarray(audio, dtype=np.float32)
            audio = audio.reshape(-1, 1)
            logger.debug(f"Audio shape: {audio.shape}, dtype: {audio.dtype}")

            # Save to file
            sf.write(audio_path, audio, self.sample_rate)
            logger.info(f"Successfully saved audio file: {audio_path}")

            return audio_path, self.sample_rate
        except Exception as e:
            logger.error(f"Failed to generate Bark audio: {e}", exc_info=True)
            raise RuntimeError(f"Failed to generate Bark audio: {e}") from e

    def get_engine_name(self) -> str:
        """Return the name of the TTS engine."""
        return "Live Bark TTS"

    def _print_engine_specific_info(self):
        """Print Bark-specific configuration info."""
        print(f"Voice preset: {self.voice_preset}")
        print(f"Sample rate: {self.sample_rate} Hz")
