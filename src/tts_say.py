"""macOS 'say' command TTS engine implementation."""

import subprocess
from typing import Tuple, Optional

from .tts_base import TTSEngine


class SayTTSEngine(TTSEngine):
    """TTS engine using macOS built-in 'say' command."""

    def __init__(
        self, output_devices: list, voice: Optional[str] = None, tmp_dir: str = None
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

        subprocess.run(cmd, check=True)

        # macOS 'say' typically outputs at 22050 Hz, but soundfile will read the actual rate
        return audio_path, 22050

    def get_engine_name(self) -> str:
        """Return the name of the TTS engine."""
        return "Live TTS (macOS say)"

    def _print_engine_specific_info(self):
        """Print Say-specific configuration info."""
        if self.voice:
            print(f"Voice: {self.voice}")
        else:
            print("Voice: Default")
