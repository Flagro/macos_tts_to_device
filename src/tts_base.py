"""Base class for TTS engines."""

import os
import uuid
import logging
import threading
from abc import ABC, abstractmethod
from typing import Optional, Any

import sounddevice as sd
import soundfile as sf

logger = logging.getLogger(__name__)


class TTSEngine(ABC):
    """Base class for TTS engines with multi-device playback support."""

    def __init__(self, output_devices: list[str], tmp_dir: Optional[str] = None):
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
        try:
            os.makedirs(self.tmp_dir, exist_ok=True)
            logger.info(f"Temporary directory: {self.tmp_dir}")
        except OSError as e:
            logger.error(f"Failed to create temporary directory {self.tmp_dir}: {e}")
            raise RuntimeError(
                f"Failed to create temporary directory {self.tmp_dir}: {e}"
            ) from e

    @abstractmethod
    def generate_audio(self, text: str) -> tuple[str, int]:
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

    @staticmethod
    @abstractmethod
    def print_available_voices():
        """
        Print a formatted list of available voices for this TTS engine.

        This method should be implemented as a static method that displays
        all available voices in a user-friendly format.
        """
        pass

    @staticmethod
    def list_available_devices() -> list[dict[str, Any]]:
        """
        Get a list of all available audio devices.

        Returns:
            List of dictionaries containing device information with keys:
            - name: Device name
            - index: Device index
            - max_output_channels: Number of output channels
            - default_samplerate: Default sample rate
            - hostapi: Host API index
        """
        try:
            devices = sd.query_devices()
            output_devices = []

            # Filter for output devices (those with output channels)
            if isinstance(devices, list):
                for idx, device in enumerate(devices):
                    if device["max_output_channels"] > 0:
                        output_devices.append(
                            {
                                "name": device["name"],
                                "index": idx,
                                "max_output_channels": device["max_output_channels"],
                                "default_samplerate": device["default_samplerate"],
                                "hostapi": device["hostapi"],
                            }
                        )
            else:
                # Single device returned
                if devices["max_output_channels"] > 0:
                    output_devices.append(
                        {
                            "name": devices["name"],
                            "index": 0,
                            "max_output_channels": devices["max_output_channels"],
                            "default_samplerate": devices["default_samplerate"],
                            "hostapi": devices["hostapi"],
                        }
                    )

            logger.info(f"Found {len(output_devices)} output devices")
            return output_devices
        except Exception as e:
            logger.error(f"Failed to query audio devices: {e}", exc_info=True)
            raise RuntimeError(f"Failed to query audio devices: {e}") from e

    @staticmethod
    def print_available_devices():
        """Print a formatted list of all available audio output devices."""
        try:
            devices = TTSEngine.list_available_devices()
            default_device = (
                sd.default.device[1]
                if isinstance(sd.default.device, (list, tuple))
                else sd.default.device
            )

            print(f"\nAvailable Audio Output Devices ({len(devices)} total):\n")
            print(f"{'Index':<6} {'Channels':<9} {'Sample Rate':<12} {'Device Name'}")
            print("-" * 80)

            for device in devices:
                is_default = " (default)" if device["index"] == default_device else ""
                print(
                    f"{device['index']:<6} "
                    f"{device['max_output_channels']:<9} "
                    f"{int(device['default_samplerate']):<12} "
                    f"{device['name']}{is_default}"
                )

            print("\nUsage:")
            print("  - Use device name: --device 'Device Name'")
            print("  - Use device index: --device 0")
            print("  - Multiple devices: --device 'Device 1' --device 'Device 2'")
        except Exception as e:
            print(f"Error listing audio devices: {e}")
            logger.error(f"Error in print_available_devices: {e}", exc_info=True)

    def play_on_device(self, audio_path: str, sample_rate: int, device_name: str):
        """
        Play audio file on a specific device.

        Args:
            audio_path: Path to audio file
            sample_rate: Sample rate of the audio
            device_name: Name or ID of the output device
        """
        try:
            logger.debug(f"Reading audio file for device '{device_name}': {audio_path}")
            data, sr = sf.read(audio_path, dtype="float32", always_2d=True)
            logger.debug(
                f"Playing audio on device '{device_name}': {data.shape[0]} samples at {sr} Hz"
            )
            sd.play(data, sr, device=device_name)
            sd.wait()
            logger.info(f"Finished playback on device '{device_name}'")
        except Exception as e:
            logger.error(f"Error playing on device '{device_name}': {e}", exc_info=True)
            print(f"Error playing on device '{device_name}': {e}")

    def play_audio(self, audio_path: str, sample_rate: int):
        """
        Play audio file on all configured output devices simultaneously.

        Args:
            audio_path: Path to audio file
            sample_rate: Sample rate of the audio
        """
        logger.info(
            f"Starting playback on {len(self.output_devices)} device(s): {self.output_devices}"
        )
        threads = []
        for device in self.output_devices:
            thread = threading.Thread(
                target=self.play_on_device,
                args=(audio_path, sample_rate, device),
                name=f"Playback-{device}",
            )
            thread.start()
            threads.append(thread)

        # Wait for all devices to finish playing
        for thread in threads:
            thread.join()
        logger.info("All devices finished playback")

    def process_text(self, text: str):
        """
        Process text input: generate audio and play it on all devices.

        Args:
            text: Text to convert to speech
        """
        audio_path = None
        logger.info(f"Processing text: '{text[:50]}{'...' if len(text) > 50 else ''}'")
        try:
            audio_path, sample_rate = self.generate_audio(text)
            self.play_audio(audio_path, sample_rate)
        finally:
            if audio_path and os.path.exists(audio_path):
                try:
                    os.remove(audio_path)
                    logger.debug(f"Cleaned up temporary file: {audio_path}")
                except OSError as e:
                    logger.warning(f"Failed to remove temporary file {audio_path}: {e}")

    def generate_temp_path(self, extension: str = "wav") -> str:
        """
        Generate a unique temporary file path.

        Args:
            extension: File extension (default: wav)

        Returns:
            Full path to temporary file
        """
        temp_path = os.path.join(self.tmp_dir, f"{uuid.uuid4().hex}.{extension}")
        logger.debug(f"Generated temporary file path: {temp_path}")
        return temp_path

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
