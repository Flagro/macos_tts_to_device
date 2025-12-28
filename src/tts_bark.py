"""Bark AI TTS engine implementation."""

import logging
import numpy as np
import soundfile as sf
from typing import Tuple, List

from .tts_base import TTSEngine

logger = logging.getLogger(__name__)

# Available Bark voice presets
BARK_VOICES = {
    # English speakers
    "v2/en_speaker_0": "English Speaker 0 (Male, neutral)",
    "v2/en_speaker_1": "English Speaker 1 (Male, calm)",
    "v2/en_speaker_2": "English Speaker 2 (Male, friendly)",
    "v2/en_speaker_3": "English Speaker 3 (Male, expressive)",
    "v2/en_speaker_4": "English Speaker 4 (Male, professional)",
    "v2/en_speaker_5": "English Speaker 5 (Male, energetic)",
    "v2/en_speaker_6": "English Speaker 6 (Female, warm)",
    "v2/en_speaker_7": "English Speaker 7 (Female, clear)",
    "v2/en_speaker_8": "English Speaker 8 (Female, soft)",
    "v2/en_speaker_9": "English Speaker 9 (Female, bright)",
    # German speakers
    "v2/de_speaker_0": "German Speaker 0",
    "v2/de_speaker_1": "German Speaker 1",
    "v2/de_speaker_2": "German Speaker 2",
    "v2/de_speaker_3": "German Speaker 3",
    "v2/de_speaker_4": "German Speaker 4",
    "v2/de_speaker_5": "German Speaker 5",
    "v2/de_speaker_6": "German Speaker 6",
    "v2/de_speaker_7": "German Speaker 7",
    "v2/de_speaker_8": "German Speaker 8",
    "v2/de_speaker_9": "German Speaker 9",
    # Spanish speakers
    "v2/es_speaker_0": "Spanish Speaker 0",
    "v2/es_speaker_1": "Spanish Speaker 1",
    "v2/es_speaker_2": "Spanish Speaker 2",
    "v2/es_speaker_3": "Spanish Speaker 3",
    "v2/es_speaker_4": "Spanish Speaker 4",
    "v2/es_speaker_5": "Spanish Speaker 5",
    "v2/es_speaker_6": "Spanish Speaker 6",
    "v2/es_speaker_7": "Spanish Speaker 7",
    "v2/es_speaker_8": "Spanish Speaker 8",
    "v2/es_speaker_9": "Spanish Speaker 9",
    # French speakers
    "v2/fr_speaker_0": "French Speaker 0",
    "v2/fr_speaker_1": "French Speaker 1",
    "v2/fr_speaker_2": "French Speaker 2",
    "v2/fr_speaker_3": "French Speaker 3",
    "v2/fr_speaker_4": "French Speaker 4",
    "v2/fr_speaker_5": "French Speaker 5",
    "v2/fr_speaker_6": "French Speaker 6",
    "v2/fr_speaker_7": "French Speaker 7",
    "v2/fr_speaker_8": "French Speaker 8",
    "v2/fr_speaker_9": "French Speaker 9",
    # Hindi speakers
    "v2/hi_speaker_0": "Hindi Speaker 0",
    "v2/hi_speaker_1": "Hindi Speaker 1",
    "v2/hi_speaker_2": "Hindi Speaker 2",
    "v2/hi_speaker_3": "Hindi Speaker 3",
    "v2/hi_speaker_4": "Hindi Speaker 4",
    "v2/hi_speaker_5": "Hindi Speaker 5",
    "v2/hi_speaker_6": "Hindi Speaker 6",
    "v2/hi_speaker_7": "Hindi Speaker 7",
    "v2/hi_speaker_8": "Hindi Speaker 8",
    "v2/hi_speaker_9": "Hindi Speaker 9",
    # Italian speakers
    "v2/it_speaker_0": "Italian Speaker 0",
    "v2/it_speaker_1": "Italian Speaker 1",
    "v2/it_speaker_2": "Italian Speaker 2",
    "v2/it_speaker_3": "Italian Speaker 3",
    "v2/it_speaker_4": "Italian Speaker 4",
    "v2/it_speaker_5": "Italian Speaker 5",
    "v2/it_speaker_6": "Italian Speaker 6",
    "v2/it_speaker_7": "Italian Speaker 7",
    "v2/it_speaker_8": "Italian Speaker 8",
    "v2/it_speaker_9": "Italian Speaker 9",
    # Japanese speakers
    "v2/ja_speaker_0": "Japanese Speaker 0",
    "v2/ja_speaker_1": "Japanese Speaker 1",
    "v2/ja_speaker_2": "Japanese Speaker 2",
    "v2/ja_speaker_3": "Japanese Speaker 3",
    "v2/ja_speaker_4": "Japanese Speaker 4",
    "v2/ja_speaker_5": "Japanese Speaker 5",
    "v2/ja_speaker_6": "Japanese Speaker 6",
    "v2/ja_speaker_7": "Japanese Speaker 7",
    "v2/ja_speaker_8": "Japanese Speaker 8",
    "v2/ja_speaker_9": "Japanese Speaker 9",
    # Korean speakers
    "v2/ko_speaker_0": "Korean Speaker 0",
    "v2/ko_speaker_1": "Korean Speaker 1",
    "v2/ko_speaker_2": "Korean Speaker 2",
    "v2/ko_speaker_3": "Korean Speaker 3",
    "v2/ko_speaker_4": "Korean Speaker 4",
    "v2/ko_speaker_5": "Korean Speaker 5",
    "v2/ko_speaker_6": "Korean Speaker 6",
    "v2/ko_speaker_7": "Korean Speaker 7",
    "v2/ko_speaker_8": "Korean Speaker 8",
    "v2/ko_speaker_9": "Korean Speaker 9",
    # Polish speakers
    "v2/pl_speaker_0": "Polish Speaker 0",
    "v2/pl_speaker_1": "Polish Speaker 1",
    "v2/pl_speaker_2": "Polish Speaker 2",
    "v2/pl_speaker_3": "Polish Speaker 3",
    "v2/pl_speaker_4": "Polish Speaker 4",
    "v2/pl_speaker_5": "Polish Speaker 5",
    "v2/pl_speaker_6": "Polish Speaker 6",
    "v2/pl_speaker_7": "Polish Speaker 7",
    "v2/pl_speaker_8": "Polish Speaker 8",
    "v2/pl_speaker_9": "Polish Speaker 9",
    # Portuguese speakers
    "v2/pt_speaker_0": "Portuguese Speaker 0",
    "v2/pt_speaker_1": "Portuguese Speaker 1",
    "v2/pt_speaker_2": "Portuguese Speaker 2",
    "v2/pt_speaker_3": "Portuguese Speaker 3",
    "v2/pt_speaker_4": "Portuguese Speaker 4",
    "v2/pt_speaker_5": "Portuguese Speaker 5",
    "v2/pt_speaker_6": "Portuguese Speaker 6",
    "v2/pt_speaker_7": "Portuguese Speaker 7",
    "v2/pt_speaker_8": "Portuguese Speaker 8",
    "v2/pt_speaker_9": "Portuguese Speaker 9",
    # Russian speakers
    "v2/ru_speaker_0": "Russian Speaker 0",
    "v2/ru_speaker_1": "Russian Speaker 1",
    "v2/ru_speaker_2": "Russian Speaker 2",
    "v2/ru_speaker_3": "Russian Speaker 3",
    "v2/ru_speaker_4": "Russian Speaker 4",
    "v2/ru_speaker_5": "Russian Speaker 5",
    "v2/ru_speaker_6": "Russian Speaker 6",
    "v2/ru_speaker_7": "Russian Speaker 7",
    "v2/ru_speaker_8": "Russian Speaker 8",
    "v2/ru_speaker_9": "Russian Speaker 9",
    # Turkish speakers
    "v2/tr_speaker_0": "Turkish Speaker 0",
    "v2/tr_speaker_1": "Turkish Speaker 1",
    "v2/tr_speaker_2": "Turkish Speaker 2",
    "v2/tr_speaker_3": "Turkish Speaker 3",
    "v2/tr_speaker_4": "Turkish Speaker 4",
    "v2/tr_speaker_5": "Turkish Speaker 5",
    "v2/tr_speaker_6": "Turkish Speaker 6",
    "v2/tr_speaker_7": "Turkish Speaker 7",
    "v2/tr_speaker_8": "Turkish Speaker 8",
    "v2/tr_speaker_9": "Turkish Speaker 9",
    # Chinese speakers
    "v2/zh_speaker_0": "Chinese Speaker 0",
    "v2/zh_speaker_1": "Chinese Speaker 1",
    "v2/zh_speaker_2": "Chinese Speaker 2",
    "v2/zh_speaker_3": "Chinese Speaker 3",
    "v2/zh_speaker_4": "Chinese Speaker 4",
    "v2/zh_speaker_5": "Chinese Speaker 5",
    "v2/zh_speaker_6": "Chinese Speaker 6",
    "v2/zh_speaker_7": "Chinese Speaker 7",
    "v2/zh_speaker_8": "Chinese Speaker 8",
    "v2/zh_speaker_9": "Chinese Speaker 9",
}


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
    def get_available_voices():
        """Return a list of all available Bark voice presets."""
        return list(BARK_VOICES.keys())
