"""Bark AI TTS engine implementation."""

import logging
import numpy as np
import soundfile as sf
from typing import Optional, Any

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
        volume: float = 1.0,
        voice_id: str = "Default",
    ):
        """
        Initialize the Bark TTS engine.

        Args:
            output_devices: List of output device names or IDs
            voice_preset: Bark voice preset (e.g., "v2/en_speaker_6")
            sample_rate: Sample rate for audio output (default: 24000)
            tmp_dir: Directory for temporary audio files
            playback_speed: Playback speed multiplier (0.5-2.0, default: 1.0)
            volume: Volume multiplier (0.0-1.0, default: 1.0)
            voice_id: The requested voice ID
        """
        super().__init__(output_devices, tmp_dir, playback_speed, volume, voice_id)

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

            msg = "Preloading Bark models (this takes a while on first run)..."
            print(msg)
            logger.info(msg)
            preload_models()
            logger.info("Bark models loaded successfully")
        except ImportError as e:
            logger.error(f"Failed to import Bark: {e}")
            raise
        except Exception as e:
            logger.error(f"Failed to load Bark models: {e}", exc_info=True)
            raise RuntimeError(f"Failed to load Bark models: {e}") from e

    @classmethod
    def from_config(cls, config: dict[str, Any]) -> "BarkTTSEngine":
        """Create a BarkTTSEngine instance from configuration."""
        import settings

        voice_id = config.get("voice_id", "Default")
        # Handle "Default" option (use default Bark speaker)
        voice_to_use = (
            settings.DEFAULT_BARK_SPEAKER if voice_id == "Default" else voice_id
        )

        return cls(
            output_devices=config.get("selected_devices", []),
            voice_preset=voice_to_use,
            sample_rate=config.get("sample_rate", 24000),
            playback_speed=config.get("playback_speed", 1.0),
            volume=config.get("volume", 1.0),
            tmp_dir=config.get("tmp_dir"),
            voice_id=voice_id,
        )

    def get_config(self) -> dict[str, Any]:
        """Return current configuration."""
        return {
            "engine_id": "bark",
            "selected_devices": self.output_devices,
            "voice_id": self.voice_id,
            "sample_rate": self.sample_rate,
            "playback_speed": self.playback_speed,
            "volume": self.volume,
        }

    def generate_audio(self, text: str) -> tuple[str, int]:
        """
        Generate audio using Bark AI.
        Handles long text by splitting it into smaller chunks.

        Args:
            text: Text to convert to speech

        Returns:
            Tuple of (audio_file_path, sample_rate)
        """
        from bark import generate_audio

        audio_path = self.generate_temp_path("wav")

        logger.debug(f"Generating Bark audio with preset '{self.voice_preset}'")

        try:
            # Simple text splitting by sentence or length to avoid Bark's context limits
            # Bark works best with ~14 seconds of audio at a time
            chunks = self._split_text(text)
            all_audio = []

            for i, chunk in enumerate(chunks):
                logger.info(
                    f"Generating Bark chunk {i+1}/{len(chunks)}: '{chunk[:30]}...'"
                )
                audio_chunk = generate_audio(chunk, history_prompt=self.voice_preset)
                all_audio.append(audio_chunk)

            # Concatenate all chunks
            if len(all_audio) > 1:
                audio = np.concatenate(all_audio)
            else:
                audio = all_audio[0]

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

    def _split_text(self, text: str, max_length: int = 150) -> list[str]:
        """
        Split text into smaller chunks for Bark.

        Args:
            text: Input text
            max_length: Maximum approximate characters per chunk

        Returns:
            List of text chunks
        """
        if len(text) <= max_length:
            return [text]

        # Try to split by sentence-like punctuation
        import re

        sentences = re.split(r"(?<=[.!?])\s+", text)

        chunks = []
        current_chunk = ""

        for sentence in sentences:
            if len(current_chunk) + len(sentence) <= max_length:
                current_chunk += sentence + " "
            else:
                if current_chunk:
                    chunks.append(current_chunk.strip())

                # If a single sentence is still too long, split by words
                if len(sentence) > max_length:
                    words = sentence.split()
                    sub_chunk = ""
                    for word in words:
                        if len(sub_chunk) + len(word) <= max_length:
                            sub_chunk += word + " "
                        else:
                            chunks.append(sub_chunk.strip())
                            sub_chunk = word + " "
                    current_chunk = sub_chunk
                else:
                    current_chunk = sentence + " "

        if current_chunk:
            chunks.append(current_chunk.strip())

        return chunks

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
        """Return a list of all available Bark voice presets with descriptions."""
        return [{"id": k, "name": v} for k, v in BARK_VOICES.items()]
