"""Base class for TTS engines."""

import os
import uuid
import threading
from abc import ABC, abstractmethod
from typing import List, Tuple

import sounddevice as sd
import soundfile as sf


class TTSEngine(ABC):
    """Base class for TTS engines with multi-device playback support."""

    def __init__(self, output_devices: List[str], tmp_dir: str = None):
        """
        Initialize the TTS engine.

        Args:
            output_devices: List of output device names or IDs
            tmp_dir: Directory for temporary audio files (default: tts_tmp/)
        """
        self.output_devices = output_devices

        if tmp_dir is None:
            script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            tmp_dir = os.path.join(script_dir, "tts_tmp")

        self.tmp_dir = tmp_dir
        os.makedirs(self.tmp_dir, exist_ok=True)

    @abstractmethod
    def generate_audio(self, text: str) -> Tuple[str, int]:
        """
        Generate audio from text and return the file path and sample rate.

        Args:
            text: Text to convert to speech

        Returns:
            Tuple of (audio_file_path, sample_rate)
        """
        pass

    @abstractmethod
    def get_engine_name(self) -> str:
        """Return the name of the TTS engine."""
        pass

    def play_on_device(self, audio_path: str, sample_rate: int, device_name: str):
        """
        Play audio file on a specific device.

        Args:
            audio_path: Path to audio file
            sample_rate: Sample rate of the audio
            device_name: Name or ID of the output device
        """
        try:
            data, sr = sf.read(audio_path, dtype="float32", always_2d=True)
            sd.play(data, sr, device=device_name)
            sd.wait()
        except Exception as e:
            print(f"Error playing on device '{device_name}': {e}")

    def play_audio(self, audio_path: str, sample_rate: int):
        """
        Play audio file on all configured output devices simultaneously.

        Args:
            audio_path: Path to audio file
            sample_rate: Sample rate of the audio
        """
        threads = []
        for device in self.output_devices:
            thread = threading.Thread(
                target=self.play_on_device, args=(audio_path, sample_rate, device)
            )
            thread.start()
            threads.append(thread)

        # Wait for all devices to finish playing
        for thread in threads:
            thread.join()

    def process_text(self, text: str):
        """
        Process text input: generate audio and play it on all devices.

        Args:
            text: Text to convert to speech
        """
        audio_path = None
        try:
            audio_path, sample_rate = self.generate_audio(text)
            self.play_audio(audio_path, sample_rate)
        finally:
            if audio_path and os.path.exists(audio_path):
                os.remove(audio_path)

    def generate_temp_path(self, extension: str = "wav") -> str:
        """
        Generate a unique temporary file path.

        Args:
            extension: File extension (default: wav)

        Returns:
            Full path to temporary file
        """
        return os.path.join(self.tmp_dir, f"{uuid.uuid4().hex}.{extension}")

    def print_info(self):
        """Print information about the TTS engine configuration."""
        print(f"\n{self.get_engine_name()} → Multiple Devices")
        print(f"Output devices: {self.output_devices}")
        print(f"Temp files: {self.tmp_dir}")
        self._print_engine_specific_info()
        print("Type a line and press Enter (Ctrl+C to quit)\n")

    def _print_engine_specific_info(self):
        """Override to print engine-specific configuration info."""
        pass
