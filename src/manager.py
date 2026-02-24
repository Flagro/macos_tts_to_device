import asyncio
import logging
import threading
from pathlib import Path
from typing import Optional, Any, Callable, List, Dict

from src.tts_base import TTSEngine
from src.history import HistoryManager
from src.profiles import ProfileManager
import settings

logger = logging.getLogger(__name__)


class TTSManager:
    """
    Manager class to orchestrate TTS operations, engine lifecycle,
    and background processing.
    """

    def __init__(self):
        # State
        self.tts_engine: Optional[TTSEngine] = None
        self.current_engine_id: Optional[str] = None
        self.is_processing: bool = False
        self.processing_lock: threading.Lock = threading.Lock()
        self.cancel_event: threading.Event = threading.Event()

        # Managers
        self.history_manager = HistoryManager()
        self.profile_manager = ProfileManager()

        # Asyncio loop for background tasks
        self.loop = asyncio.new_event_loop()
        self._loop_thread = threading.Thread(target=self._run_async_loop, daemon=True)
        self._loop_thread.start()
        self._shutdown = False

        # Callbacks
        self.on_status_change: Optional[Callable[[str], None]] = None
        self.on_processing_start: Optional[Callable[[], None]] = None
        self.on_processing_end: Optional[Callable[[], None]] = None
        self.on_history_update: Optional[Callable[[], None]] = None

    def _run_async_loop(self) -> None:
        """Run the asyncio event loop in a background thread."""
        asyncio.set_event_loop(self.loop)
        self.loop.run_forever()
        self.loop.close()

    def shutdown(self) -> None:
        """
        Stop the event loop and wait for the background thread to finish.
        Call this when the application is exiting for a clean shutdown.
        """
        if self._shutdown:
            return
        self._shutdown = True
        self.loop.call_soon_threadsafe(self.loop.stop)
        self._loop_thread.join(timeout=2.0)
        if self._loop_thread.is_alive():
            logger.warning("Event loop thread did not finish within timeout")

    def set_status(self, message: str) -> None:
        """Update status via callback."""
        logger.info(f"Status: {message}")
        if self.on_status_change:
            self.on_status_change(message)

    def update_engine(
        self,
        engine_id: str,
        selected_devices: List[str],
        voice_id: str,
        sample_rate: int,
        playback_speed: float,
        volume: float,
    ) -> bool:
        """
        Recreate or update the TTS engine with current settings.
        Returns True if successful.
        """
        config = {
            "engine_id": engine_id,
            "selected_devices": selected_devices,
            "voice_id": voice_id,
            "sample_rate": sample_rate,
            "playback_speed": playback_speed,
            "volume": volume,
        }
        return self.update_engine_from_config(config)

    def update_engine_from_config(self, config: Dict[str, Any]) -> bool:
        """
        Recreate or update the TTS engine from a configuration dictionary.
        Returns True if successful.
        """
        if not config.get("selected_devices"):
            self.set_status("Error: Please select at least one output device")
            return False

        engine_id = config["engine_id"]
        try:
            self.set_status("Initializing engine...")
            engine_registry = TTSEngine.get_registered_engines()
            if engine_id not in engine_registry:
                raise ValueError(f"Unknown engine type: {engine_id}")

            engine_class = engine_registry[engine_id]
            self.tts_engine = engine_class.from_config(config)
            self.current_engine_id = engine_id

            # Success message
            num_devices = len(config["selected_devices"])
            plural = "" if num_devices == 1 else "s"
            device_count_str = f"{num_devices} device{plural}"
            speed = config["playback_speed"]
            speed_info = f" @ {speed:.1f}x" if speed != 1.0 else ""
            volume = config["volume"]
            vol_info = f" (Vol: {int(volume * 100)}%)" if volume != 1.0 else ""

            engine_display_name = getattr(engine_class, "display_name", engine_id)
            self.set_status(
                f"Ready - Using {engine_display_name} ({device_count_str}){speed_info}{vol_info}"
            )
            return True

        except Exception as e:
            self.set_status(f"Error initializing engine: {e}")
            logger.error(f"Failed to initialize engine: {e}", exc_info=True)
            return False

    def speak(self, text: str, config: Dict[str, Any]) -> None:
        """Speak text using the current engine and configuration."""
        self._process(text, config, output_path=None, play_audio=True)

    def export(self, text: str, config: Dict[str, Any], output_path: str) -> None:
        """Export text to a file using the current engine and configuration."""
        self._process(text, config, output_path=output_path, play_audio=False)

    def stop(self) -> None:
        """Stop current processing."""
        with self.processing_lock:
            if not self.is_processing:
                return
            self.cancel_event.set()
        self.set_status("Stopping...")
        logger.info("Stop requested by user")

    def _process(
        self,
        text: str,
        config: Dict[str, Any],
        output_path: Optional[str],
        play_audio: bool,
    ) -> None:
        """Internal method to start a speech task."""
        with self.processing_lock:
            if self.is_processing:
                self.set_status("Already processing...")
                return
            self.is_processing = True

        if not text:
            self.set_status("Please enter some text")
            with self.processing_lock:
                self.is_processing = False
            return

        # Ensure engine is up to date with config
        if self._needs_reinit(config):
            success = self.update_engine_from_config(config)
            if not success:
                with self.processing_lock:
                    self.is_processing = False
                return

        self.cancel_event.clear()
        if self.on_processing_start:
            self.on_processing_start()

        # Run asynchronously
        asyncio.run_coroutine_threadsafe(
            self._process_async(text, config, output_path, play_audio), self.loop
        )

    def _needs_reinit(self, config: Dict[str, Any]) -> bool:
        """Check if engine needs re-initialization based on new config."""
        if not self.tts_engine or self.current_engine_id != config["engine_id"]:
            return True

        current_config = self.tts_engine.get_config()

        # Check common parameters
        if set(current_config["selected_devices"]) != set(config["selected_devices"]):
            return True

        if abs(current_config["playback_speed"] - config["playback_speed"]) > 0.01:
            return True

        if abs(current_config["volume"] - config["volume"]) > 0.01:
            return True

        if current_config["voice_id"] != config["voice_id"]:
            return True

        # engine specific
        if config["engine_id"] == "bark":
            if current_config.get("sample_rate") != config["sample_rate"]:
                return True

        return False

    async def _process_async(
        self,
        text: str,
        config: Dict[str, Any],
        output_path: Optional[str],
        play_audio: bool,
    ) -> None:
        """Asynchronous processing task."""
        is_bark = config["engine_id"] == "bark"

        if is_bark:
            self.set_status(
                "Generating speech with Bark AI (this may take 5-15 seconds)..."
            )
        else:
            self.set_status(
                "Exporting speech..."
                if output_path and not play_audio
                else "Generating speech..."
            )

        try:
            if not self.tts_engine:
                self.set_status("Error: Engine not initialized")
                return

            await self.tts_engine.async_process_text(
                text, self.cancel_event, output_path=output_path, play_audio=play_audio
            )

            if self.cancel_event.is_set():
                self.set_status("Stopped")
            else:
                if output_path and not play_audio:
                    self.set_status(f"Exported to {Path(output_path).name}")
                else:
                    self.set_status("Playback complete")

                # Record in history
                self.history_manager.add_entry(
                    text=text,
                    engine_id=config["engine_id"],
                    voice=config["voice_id"],
                    speed=config["playback_speed"],
                    devices=config["selected_devices"],
                    volume=config["volume"],
                    sample_rate=str(config["sample_rate"]) if is_bark else None,
                )
                if self.on_history_update:
                    self.on_history_update()

        except Exception as e:
            self.set_status(f"Error: {e}")
            logger.error(f"Error during TTS processing: {e}", exc_info=True)
        finally:
            with self.processing_lock:
                self.is_processing = False
            if self.on_processing_end:
                self.on_processing_end()
