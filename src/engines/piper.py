"""Piper TTS engine implementation."""

import logging
import wave
from pathlib import Path
from typing import Optional, Any

from ..tts_base import TTSEngine
import settings

logger = logging.getLogger(__name__)


@TTSEngine.register("piper")
class PiperTTSEngine(TTSEngine):
    """TTS engine using Piper (fast, local neural TTS)."""

    display_name = "Piper TTS (Fast & Local)"
    supports_sample_rate = False

    def __init__(
        self,
        output_devices: list[str],
        model_path: Optional[str] = None,
        tmp_dir: Optional[str] = None,
        playback_speed: float = 1.0,
        volume: float = 1.0,
        voice_id: str = "Default",
    ):
        """
        Initialize the Piper TTS engine.

        Args:
            output_devices: List of output device names or IDs
            model_path: Path to the .onnx model file
            tmp_dir: Directory for temporary audio files
            playback_speed: Playback speed multiplier (0.5-2.0, default: 1.0)
            volume: Volume multiplier (0.0-1.0, default: 1.0)
            voice_id: The requested voice ID
        """
        super().__init__(output_devices, tmp_dir, playback_speed, volume, voice_id)

        self.model_path = model_path or settings.PIPER_MODEL_PATH
        self.voice = None

        logger.info(
            f"Initialized PiperTTSEngine with model='{self.model_path}', devices={output_devices}"
        )

        # Lazy import and model loading
        try:
            from piper.voice import PiperVoice

            # Ensure model exists
            if not Path(self.model_path).exists():
                raise RuntimeError(
                    f"Piper model not found at {self.model_path}. "
                    "Please download a model and set PIPER_MODEL_PATH."
                )

            logger.info(f"Loading Piper model: {self.model_path}")
            self.voice = PiperVoice.load(self.model_path)
            logger.info("Piper model loaded successfully")
        except ImportError:
            logger.error("Piper not installed. Install with: uv pip install .[piper]")
            raise
        except Exception as e:
            logger.error(f"Failed to load Piper model: {e}", exc_info=True)
            raise RuntimeError(f"Failed to load Piper model: {e}") from e

    @classmethod
    def from_config(cls, config: dict[str, Any]) -> "PiperTTSEngine":
        """Create a PiperTTSEngine instance from configuration."""
        import settings

        voice_id = config.get("voice_id", "Default")
        # Handle "Default" option
        voice_to_use = (
            settings.PIPER_MODEL_PATH
            if voice_id == "Default"
            else str(Path(settings.PIPER_VOICES_DIR) / voice_id)
        )

        return cls(
            output_devices=config.get("selected_devices", []),
            model_path=voice_to_use,
            playback_speed=config.get("playback_speed", 1.0),
            volume=config.get("volume", 1.0),
            tmp_dir=config.get("tmp_dir"),
            voice_id=voice_id,
        )

    def get_config(self) -> dict[str, Any]:
        """Return current configuration."""
        return {
            "engine_id": "piper",
            "selected_devices": self.output_devices,
            "voice_id": self.voice_id,
            "playback_speed": self.playback_speed,
            "volume": self.volume,
            "sample_rate": 0,  # Determined by model
        }

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
        print(f"Piper Model: {Path(self.model_path).name}")

    @staticmethod
    def list_available_voices() -> list[dict[str, str]]:
        """
        List available Piper models in the models directory.
        """
        voices_dir = Path(settings.PIPER_VOICES_DIR)
        if not voices_dir.exists():
            return []

        models = [f.name for f in voices_dir.iterdir() if f.suffix == ".onnx"]
        return [{"id": m, "name": m} for m in sorted(models)]

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
            print(f"  {model['name']}")
        print("-" * 60)
        print(f"Put new models in: {settings.PIPER_VOICES_DIR}")
