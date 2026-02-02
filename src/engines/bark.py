"""Bark AI TTS engine implementation."""

import logging
import numpy as np
import soundfile as sf
from typing import Optional

from ..tts_base import TTSEngine
from settings import BARK_VOICES

logger = logging.getLogger(__name__)


@TTSEngine.register("bark")
class BarkTTSEngine(TTSEngine):
    """TTS engine using Suno's Bark AI model."""

    display_name = "Bark AI (Natural)"
    supports_sample_rate = True

    def __init__(
        self,
        output_devices: list[str],
        voice_preset: str = "v2/en_speaker_6",
        sample_rate: int = 24000,
        tmp_dir: Optional[str] = None,
        playback_speed: float = 1.0,
    ):
        """
        Initialize the Bark TTS engine.

        Args:
            output_devices: List of output device names or IDs
            voice_preset: Bark voice preset (e.g., "v2/en_speaker_6")
            sample_rate: Sample rate for audio output (default: 24000)
            tmp_dir: Directory for temporary audio files
            playback_speed: Playback speed multiplier (0.5-2.0, default: 1.0)
        """
        super().__init__(output_devices, tmp_dir, playback_speed)

        # Validate voice preset
        if voice_preset not in BARK_VOICES:
            logger.warning(
                f"Voice preset '{voice_preset}' not in known voices list. "
                f"It may still work, but consider using one of the standard presets."
            )

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

    def generate_audio(self, text: str) -> tuple[str, int]:
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

    supports_sample_rate = True

    def _print_engine_specific_info(self):
        """Print Bark-specific configuration info."""
        voice_description = BARK_VOICES.get(self.voice_preset, "Unknown voice")
        print(f"Voice preset: {self.voice_preset} ({voice_description})")
        print(f"Sample rate: {self.sample_rate} Hz")

    @staticmethod
    def print_available_voices():
        """Print all available Bark voice presets."""
        print("\nAvailable Bark Voice Presets:")
        print("=" * 60)

        # Group by language
        languages = {}
        for voice_id, description in BARK_VOICES.items():
            lang_code = voice_id.split("/")[1].split("_")[0]
            if lang_code not in languages:
                languages[lang_code] = []
            languages[lang_code].append((voice_id, description))

        # Sort and print by language
        for lang_code in sorted(languages.keys()):
            lang_names = {
                "en": "English",
                "de": "German",
                "es": "Spanish",
                "fr": "French",
                "hi": "Hindi",
                "it": "Italian",
                "ja": "Japanese",
                "ko": "Korean",
                "pl": "Polish",
                "pt": "Portuguese",
                "ru": "Russian",
                "tr": "Turkish",
                "zh": "Chinese",
            }
            lang_name = lang_names.get(lang_code, lang_code.upper())
            print(f"\n{lang_name}:")
            print("-" * 60)

            for voice_id, description in sorted(languages[lang_code]):
                print(f"  {voice_id:<25} {description}")

        print("\n" + "=" * 60)
        print("Usage: python main.py --engine bark --speaker <voice_preset>")
        print("Example: python main.py --engine bark --speaker v2/en_speaker_3")

    @staticmethod
    def list_available_voices():
        """Return a list of all available Bark voice presets."""
        return list(BARK_VOICES.keys())
