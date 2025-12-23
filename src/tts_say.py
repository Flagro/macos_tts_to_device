"""macOS 'say' command TTS engine implementation."""

import logging
import subprocess
from typing import Tuple, Optional, List

import soundfile as sf

from .tts_base import TTSEngine

logger = logging.getLogger(__name__)


class SayTTSEngine(TTSEngine):
    """TTS engine using macOS built-in 'say' command."""

    def __init__(
        self,
        output_devices: List[str],
        voice: Optional[str] = None,
        tmp_dir: str = None,
    ):
        """
        Initialize the Say TTS engine.

        Args:
            output_devices: List of output device names or IDs
            voice: macOS voice name (e.g., "Alex", "Samantha"), None for default
            tmp_dir: Directory for temporary audio files
        """
        super().__init__(output_devices, tmp_dir)
        self.voice = voice
        logger.info(
            f"Initialized SayTTSEngine with voice='{voice}', devices={output_devices}"
        )

    def generate_audio(self, text: str) -> Tuple[str, int]:
        """
        Generate audio using macOS 'say' command.

        Args:
            text: Text to convert to speech

        Returns:
            Tuple of (audio_file_path, sample_rate)
        """
        audio_path = self.generate_temp_path("aiff")

        # Build 'say' command
        cmd = ["say"]
        if self.voice:
            cmd += ["-v", self.voice]
        cmd += [text, "-o", audio_path]

        logger.debug(f"Executing command: {' '.join(cmd)}")

        try:
            result = subprocess.run(
                cmd, check=True, capture_output=True, text=True, timeout=30
            )
            if result.stdout:
                logger.debug(f"Command stdout: {result.stdout}")
            if result.stderr:
                logger.warning(f"Command stderr: {result.stderr}")
            logger.info(f"Successfully generated audio file: {audio_path}")
        except subprocess.TimeoutExpired as e:
            logger.error(f"Command timed out after 30 seconds: {' '.join(cmd)}")
            raise RuntimeError(
                f"The 'say' command timed out after 30 seconds. Text may be too long."
            ) from e
        except subprocess.CalledProcessError as e:
            logger.error(
                f"Command failed with exit code {e.returncode}: {' '.join(cmd)}"
            )
            logger.error(f"stderr: {e.stderr}")
            logger.error(f"stdout: {e.stdout}")
            raise RuntimeError(
                f"Failed to generate audio with 'say' command: {e.stderr.strip() if e.stderr else 'Unknown error'}"
            ) from e
        except FileNotFoundError as e:
            logger.error(f"'say' command not found. Is this running on macOS?")
            raise RuntimeError(
                "The 'say' command was not found. This tool requires macOS."
            ) from e

        # Read the actual sample rate from the generated audio file
        try:
            info = sf.info(audio_path)
            logger.debug(
                f"Audio file info: sample_rate={info.samplerate}, channels={info.channels}, duration={info.duration:.2f}s"
            )
            return audio_path, info.samplerate
        except Exception as e:
            logger.error(f"Failed to read audio file info from {audio_path}: {e}")
            raise RuntimeError(f"Failed to read generated audio file: {e}") from e

    def get_engine_name(self) -> str:
        """Return the name of the TTS engine."""
        return "Live TTS (macOS say)"

    def _print_engine_specific_info(self):
        """Print Say-specific configuration info."""
        if self.voice:
            print(f"Voice: {self.voice}")
        else:
            print("Voice: Default")
