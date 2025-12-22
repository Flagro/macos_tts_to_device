"""macOS 'say' command TTS engine implementation."""

import subprocess
from typing import Tuple, Optional, List

import soundfile as sf

from .tts_base import TTSEngine


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

        try:
            subprocess.run(cmd, check=True, capture_output=True, text=True)
        except subprocess.CalledProcessError as e:
            raise RuntimeError(
                f"Failed to generate audio with 'say' command: {e.stderr}"
            )

        # Read the actual sample rate from the generated audio file
        info = sf.info(audio_path)
        return audio_path, info.samplerate

    def get_engine_name(self) -> str:
        """Return the name of the TTS engine."""
        return "Live TTS (macOS say)"

    def _print_engine_specific_info(self):
        """Print Say-specific configuration info."""
        if self.voice:
            print(f"Voice: {self.voice}")
        else:
            print("Voice: Default")
