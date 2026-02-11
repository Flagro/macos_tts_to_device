"""Base class for TTS engines."""

import os
import uuid
import logging
import threading
import asyncio
from abc import ABC, abstractmethod
from typing import Optional, Any

import numpy as np
import sounddevice as sd
import soundfile as sf
from scipy import signal

import settings

logger = logging.getLogger(__name__)


class TTSEngine(ABC):
    """Base class for TTS engines with multi-device playback support."""

    _registry: dict[str, type["TTSEngine"]] = {}

    @classmethod
    def register(cls, engine_id: str):
        """Decorator to register a TTS engine."""

        def wrapper(subclass):
            cls._registry[engine_id] = subclass
            subclass.engine_id = engine_id
            return subclass

        return wrapper

    @classmethod
    def get_registered_engines(cls) -> dict[str, type["TTSEngine"]]:
        """Get all registered TTS engines."""
        return cls._registry

    @classmethod
    def get_engine_class(cls, engine_id: str) -> type["TTSEngine"]:
        """Get a registered engine class by ID."""
        if engine_id not in cls._registry:
            raise ValueError(f"Engine '{engine_id}' not found in registry.")
        return cls._registry[engine_id]

    @classmethod
    def list_engines(cls):
        """Print a list of all registered engines and their descriptions."""
        print(f"\nAvailable TTS Engines ({len(cls._registry)} total):")
        print("-" * 60)
        for engine_id, engine_class in cls._registry.items():
            print(f"  {engine_id:<10} {engine_class.display_name}")
        print("-" * 60)

    @classmethod
    def resolve_device(cls, device_name_or_index: Any) -> Any:
        """
        Resolve a device name or index to a valid sounddevice device.

        Args:
            device_name_or_index: Name (str), partial name (str), or index (int)

        Returns:
            The resolved device name or index that sounddevice can use.
            Returns the input if no better match is found.
        """
        try:
            # If it's already an index, just return it
            if isinstance(device_name_or_index, int):
                return device_name_or_index

            # If it's a string that looks like an index
            if isinstance(device_name_or_index, str) and device_name_or_index.isdigit():
                return int(device_name_or_index)

            # Otherwise, try to find a matching name
            devices = sd.query_devices()

            # Try exact match first
            for i, dev in enumerate(devices):
                if (
                    dev["name"] == device_name_or_index
                    and dev["max_output_channels"] > 0
                ):
                    return device_name_or_index

            # Try partial match (case-insensitive)
            search_name = str(device_name_or_index).lower()
            for i, dev in enumerate(devices):
                if (
                    search_name in dev["name"].lower()
                    and dev["max_output_channels"] > 0
                ):
                    logger.info(f"Resolved '{device_name_or_index}' to '{dev['name']}'")
                    return dev["name"]

            # If no match found and it was the default device from settings, try to find ANY output device
            if device_name_or_index == settings.PREFERRED_DEFAULT_DEVICE:
                # Try to get the system default output device
                default_device = sd.default.device[1]  # index 1 is output
                if default_device >= 0:
                    dev_info = sd.query_devices(default_device)
                    logger.info(
                        f"Default device '{device_name_or_index}' not found. Using system default: '{dev_info['name']}'"
                    )
                    return dev_info["name"]

            return device_name_or_index
        except Exception as e:
            logger.warning(f"Failed to resolve device '{device_name_or_index}': {e}")
            return device_name_or_index

    display_name: str = "Base TTS Engine"
    supports_sample_rate: bool = False

    def __init__(
        self,
        output_devices: list[str],
        tmp_dir: Optional[str] = None,
        playback_speed: float = 1.0,
        volume: float = 1.0,
        voice_id: str = "Default",
    ):
        """
        Initialize the TTS engine.

        Args:
            output_devices: List of output device names or IDs
            tmp_dir: Directory for temporary audio files (default: tts_tmp/)
            playback_speed: Playback speed multiplier (0.5-2.0, default: 1.0)
            volume: Volume multiplier (0.0-1.0, default: 1.0)
            voice_id: The requested voice ID (e.g., "Default" or specific voice)
        """
        # Resolve all devices
        self.output_devices = [self.resolve_device(d) for d in output_devices]
        self.playback_speed = max(0.5, min(2.0, playback_speed))  # Clamp to range
        self.volume = max(0.0, min(1.0, volume))  # Clamp to range
        self.voice_id = voice_id

        if tmp_dir is None:
            script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            tmp_dir = os.path.join(script_dir, "tts_tmp")

        self.tmp_dir = tmp_dir
        try:
            os.makedirs(self.tmp_dir, exist_ok=True)
            logger.info(f"Temporary directory: {self.tmp_dir}")
            logger.info(f"Playback speed: {self.playback_speed}x")
        except OSError as e:
            logger.error(f"Failed to create temporary directory {self.tmp_dir}: {e}")
            raise RuntimeError(
                f"Failed to create temporary directory {self.tmp_dir}: {e}"
            ) from e

    @classmethod
    @abstractmethod
    def from_config(cls, config: dict[str, Any]) -> "TTSEngine":
        """
        Create an engine instance from a configuration dictionary.

        Args:
            config: Dictionary containing engine settings:
                - selected_devices: list[str]
                - voice_id: str
                - sample_rate: int
                - playback_speed: float
                - volume: float
                - (optional) tmp_dir: str
        """
        pass

    @abstractmethod
    def get_config(self) -> dict[str, Any]:
        """
        Return the current configuration of the engine.
        Used to determine if re-initialization is needed.
        """
        pass

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
    def list_available_voices() -> list[Any]:
        """
        Return a list of available voices/presets for this TTS engine.
        """
        pass

    @staticmethod
    @abstractmethod
    def print_available_voices():
        """
        Print a formatted list of available voices for this TTS engine.
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

            # Safely get the default output device index
            try:
                default_val = sd.default.device
                if isinstance(default_val, (list, tuple)):
                    default_device = default_val[1]
                else:
                    default_device = int(default_val)
            except (AttributeError, TypeError, ValueError, IndexError):
                default_device = -1

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

    def play_on_device(
        self,
        audio_path: str,
        sample_rate: int,
        device_name: str,
        cancel_event: Optional[threading.Event] = None,
    ):
        """
        Play audio file on a specific device.

        Args:
            audio_path: Path to audio file
            sample_rate: Sample rate of the audio
            device_name: Name or ID of the output device
            cancel_event: Optional threading.Event to signal cancellation
        """
        try:
            # Check if cancelled before starting
            if cancel_event and cancel_event.is_set():
                logger.info(
                    f"Playback cancelled before starting on device '{device_name}'"
                )
                return

            logger.debug(f"Reading audio file for device '{device_name}': {audio_path}")
            data, sr = sf.read(audio_path, dtype="float32", always_2d=True)

            # Apply volume adjustment
            if self.volume != 1.0:
                data = data * self.volume
                logger.debug(f"Applied volume adjustment: {self.volume}x")

            # Apply playback speed adjustment if needed
            if self.playback_speed != 1.0:
                data = self._apply_speed_adjustment(data, self.playback_speed)
                logger.debug(
                    f"Applied {self.playback_speed}x speed adjustment on device '{device_name}'"
                )

            logger.debug(
                f"Playing audio on device '{device_name}': {data.shape[0]} samples at {sr} Hz"
            )
            sd.play(data, sr, device=device_name)

            # Wait with periodic cancellation checks
            while sd.get_stream().active:
                if cancel_event and cancel_event.is_set():
                    sd.stop()
                    logger.info(f"Playback cancelled on device '{device_name}'")
                    return
                sd.sleep(100)  # Check every 100ms

            logger.info(f"Finished playback on device '{device_name}'")
        except Exception as e:
            logger.error(f"Error playing on device '{device_name}': {e}", exc_info=True)
            print(f"Error playing on device '{device_name}': {e}")

    def play_audio(
        self,
        audio_path: str,
        sample_rate: int,
        cancel_event: Optional[threading.Event] = None,
    ):
        """
        Play audio file on all configured output devices simultaneously.

        Args:
            audio_path: Path to audio file
            sample_rate: Sample rate of the audio
            cancel_event: Optional threading.Event to signal cancellation
        """
        logger.info(
            f"Starting playback on {len(self.output_devices)} device(s): {self.output_devices}"
        )
        threads = []
        for device in self.output_devices:
            thread = threading.Thread(
                target=self.play_on_device,
                args=(audio_path, sample_rate, device, cancel_event),
                name=f"Playback-{device}",
            )
            thread.start()
            threads.append(thread)

        # Wait for all devices to finish playing
        for thread in threads:
            thread.join()
        logger.info("All devices finished playback")

    def process_text(
        self,
        text: str,
        cancel_event: Optional[threading.Event] = None,
        output_path: Optional[str] = None,
        play_audio: bool = True,
    ):
        """
        Process text input: generate audio and optionally play/save it.

        Args:
            text: Text to convert to speech
            cancel_event: Optional threading.Event to signal cancellation
            output_path: Optional path to save the generated audio file
            play_audio: Whether to play the audio on configured devices
        """
        audio_path = None
        logger.info(f"Processing text: '{text[:50]}{'...' if len(text) > 50 else ''}'")
        try:
            # Check if cancelled before generating
            if cancel_event and cancel_event.is_set():
                logger.info("Text processing cancelled before audio generation")
                return

            audio_path, sample_rate = self.generate_audio(text)

            # Check if cancelled after generation
            if cancel_event and cancel_event.is_set():
                logger.info("Text processing cancelled after audio generation")
                return

            # Save to output path if provided
            if output_path:
                import shutil

                shutil.copy2(audio_path, output_path)
                logger.info(f"Exported audio to: {output_path}")

            # Play audio if requested
            if play_audio:
                self.play_audio(audio_path, sample_rate, cancel_event)

        finally:
            if audio_path and os.path.exists(audio_path):
                try:
                    os.remove(audio_path)
                    logger.debug(f"Cleaned up temporary file: {audio_path}")
                except OSError as e:
                    logger.warning(f"Failed to remove temporary file {audio_path}: {e}")

    async def async_process_text(
        self,
        text: str,
        cancel_event: Optional[threading.Event] = None,
        output_path: Optional[str] = None,
        play_audio: bool = True,
    ):
        """
        Asynchronously process text input.

        Args:
            text: Text to convert to speech
            cancel_event: Optional threading.Event to signal cancellation
            output_path: Optional path to save the generated audio file
            play_audio: Whether to play the audio on configured devices
        """
        audio_path = None
        logger.info(
            f"Async processing text: '{text[:50]}{'...' if len(text) > 50 else ''}'"
        )
        try:
            if cancel_event and cancel_event.is_set():
                return

            # Run generation in a thread to keep the event loop free
            audio_path, sample_rate = await asyncio.to_thread(self.generate_audio, text)

            if cancel_event and cancel_event.is_set():
                return

            # Save to output path if provided
            if output_path:
                import shutil

                await asyncio.to_thread(shutil.copy2, audio_path, output_path)
                logger.info(f"Exported audio to: {output_path}")

            # Play audio if requested
            if play_audio:
                await self.async_play_audio(audio_path, sample_rate, cancel_event)
        finally:
            if audio_path and os.path.exists(audio_path):
                try:
                    await asyncio.to_thread(os.remove, audio_path)
                    logger.debug(f"Cleaned up temporary file: {audio_path}")
                except OSError as e:
                    logger.warning(f"Failed to remove temporary file {audio_path}: {e}")

    async def async_play_audio(
        self,
        audio_path: str,
        sample_rate: int,
        cancel_event: Optional[threading.Event] = None,
    ):
        """
        Asynchronously play audio on all devices.

        Args:
            audio_path: Path to audio file
            sample_rate: Sample rate of the audio
            cancel_event: Optional threading.Event to signal cancellation
        """
        logger.info(f"Starting async playback on {len(self.output_devices)} device(s)")
        tasks = []
        for device in self.output_devices:
            tasks.append(
                asyncio.to_thread(
                    self.play_on_device, audio_path, sample_rate, device, cancel_event
                )
            )
        await asyncio.gather(*tasks)

    def _apply_speed_adjustment(
        self, audio_data: np.ndarray, speed: float
    ) -> np.ndarray:
        """
        Apply playback speed adjustment to audio data using resampling.

        This method speeds up or slows down audio playback by resampling.
        Note: This changes both tempo and pitch (like a record player).

        Args:
            audio_data: Audio data as numpy array (samples x channels)
            speed: Speed multiplier (0.5 = half speed, 2.0 = double speed)

        Returns:
            Resampled audio data
        """
        if speed == 1.0:
            return audio_data

        # Calculate new number of samples
        original_length = audio_data.shape[0]
        new_length = int(original_length / speed)

        # Resample each channel
        if audio_data.ndim == 1:
            # Mono audio
            resampled = signal.resample(audio_data, new_length)
        else:
            # Multi-channel audio - resample each channel separately
            resampled = np.zeros((new_length, audio_data.shape[1]), dtype=np.float32)
            for ch in range(audio_data.shape[1]):
                resampled[:, ch] = signal.resample(audio_data[:, ch], new_length)

        return resampled.astype(np.float32)

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
        if self.playback_speed != 1.0:
            print(f"Playback speed: {self.playback_speed}x")
        self._print_engine_specific_info()
        print("Type a line and press Enter (Ctrl+C to quit)\n")

    def _print_engine_specific_info(self):
        """Override to print engine-specific configuration info."""
        pass
