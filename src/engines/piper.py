"""Piper TTS engine implementation."""

import logging
import os
import wave
from typing import Optional

from ..tts_base import TTSEngine
import settings

logger = logging.getLogger(__name__)


@TTSEngine.register("piper")
class PiperTTSEngine(TTSEngine):
    """TTS engine using Piper (fast, local neural TTS)."""

    supports_sample_rate = False

    def __init__(
        self,
        output_devices: list[str],
        model_path: Optional[str] = None,
        tmp_dir: Optional[str] = None,
        playback_speed: float = 1.0,
    ):
        """
        Initialize the Piper TTS engine.

        Args:
            output_devices: List of output device names or IDs
            model_path: Path to the .onnx model file
            tmp_dir: Directory for temporary audio files
            playback_speed: Playback speed multiplier (0.5-2.0, default: 1.0)
        """
        super().__init__(output_devices, tmp_dir, playback_speed)

        self.model_path = model_path or settings.PIPER_MODEL_PATH
        self.voice = None

        logger.info(
            f"Initialized PiperTTSEngine with model='{self.model_path}', devices={output_devices}"
        )

        # Lazy import and model loading
        try:
            from piper.voice import PiperVoice

            # Ensure model exists
            if not os.path.exists(self.model_path):
                logger.warning(
                    f"Piper model not found at {self.model_path}. "
                    f"Please download a model and set PIPER_MODEL_PATH."
                )
                return

            logger.info(f"Loading Piper model: {self.model_path}")
            self.voice = PiperVoice.load(self.model_path)
            logger.info("Piper model loaded successfully")
        except ImportError:
            logger.error("Piper not installed. Install with: uv pip install .[piper]")
            raise
        except Exception as e:
            logger.error(f"Failed to load Piper model: {e}", exc_info=True)
            raise RuntimeError(f"Failed to load Piper model: {e}") from e

    def generate_audio(self, text: str) -> tuple[str, int]:
        """
        Generate audio using Piper.

        Args:
            text: Text to convert to speech

        Returns:
            Tuple of (audio_file_path, sample_rate)
        """
        if not self.voice:
            raise RuntimeError(
                f"Piper model not loaded. Check model path: {self.model_path}"
            )

        audio_path = self.generate_temp_path("wav")
        logger.debug(f"Generating Piper audio for text: {text[:50]}...")

        try:
            with wave.open(audio_path, "wb") as wav_file:
                self.voice.synthesize(text, wav_file)

            # Get sample rate from the generated wav file
            with wave.open(audio_path, "rb") as wav_file:
                sample_rate = wav_file.getframerate()

            logger.info(f"Successfully generated Piper audio: {audio_path}")
            return audio_path, sample_rate
        except Exception as e:
            logger.error(f"Failed to generate Piper audio: {e}", exc_info=True)
            raise RuntimeError(f"Failed to generate Piper audio: {e}") from e

    def get_engine_name(self) -> str:
        """Return the name of the TTS engine."""
        return "Live Piper TTS"

    def _print_engine_specific_info(self):
        """Print Piper-specific configuration info."""
        print(f"Piper Model: {os.path.basename(self.model_path)}")

    @staticmethod
    def list_available_voices() -> list[str]:
        """
        List available Piper models in the models directory.
        """
        voices_dir = settings.PIPER_VOICES_DIR
        if not os.path.exists(voices_dir):
            return []

        models = [f for f in os.listdir(voices_dir) if f.endswith(".onnx")]
        return sorted(models)

    @staticmethod
    def print_available_voices():
        """Print all available Piper models."""
        models = PiperTTSEngine.list_available_voices()
        if not models:
            print("\nNo Piper models (.onnx) found in " + settings.PIPER_VOICES_DIR)
            print("Download models from: https://github.com/rhasspy/piper#voices")
            return

        print(f"\nAvailable Piper Models ({len(models)} total):")
        print("-" * 60)
        for model in models:
            print(f"  {model}")
        print("-" * 60)
        print(f"Put new models in: {settings.PIPER_VOICES_DIR}")
