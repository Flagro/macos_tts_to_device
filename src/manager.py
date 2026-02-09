import asyncio
import logging
import threading
import os
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

        # Callbacks
        self.on_status_change: Optional[Callable[[str], None]] = None
        self.on_processing_start: Optional[Callable[[], None]] = None
        self.on_processing_end: Optional[Callable[[], None]] = None
        self.on_history_update: Optional[Callable[[], None]] = None

    def _run_async_loop(self) -> None:
        """Run the asyncio event loop in a background thread."""
        asyncio.set_event_loop(self.loop)
        self.loop.run_forever()

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
        if not selected_devices:
            self.set_status("Error: Please select at least one output device")
            return False

        try:
            self.set_status("Initializing engine...")
            engine_registry = TTSEngine.get_registered_engines()
            if engine_id not in engine_registry:
                raise ValueError(f"Unknown engine type: {engine_id}")

            engine_class = engine_registry[engine_id]

            # Normalize voice_id for "Default" options
            voice_to_use = None
            if engine_id == "say":
                voice_to_use = None if voice_id == "Default" else voice_id
                self.tts_engine = engine_class(
                    output_devices=selected_devices,
                    voice=voice_to_use,
                    timeout=settings.SAY_ENGINE_TIMEOUT,
                    playback_speed=playback_speed,
                    volume=volume,
                )
            elif engine_id == "bark":
                voice_to_use = (
                    settings.DEFAULT_BARK_SPEAKER if voice_id == "Default" else voice_id
                )
                self.tts_engine = engine_class(
                    output_devices=selected_devices,
                    voice_preset=voice_to_use,
                    sample_rate=sample_rate,
                    playback_speed=playback_speed,
                    volume=volume,
                )
            elif engine_id == "piper":
                voice_to_use = (
                    settings.PIPER_MODEL_PATH
                    if voice_id == "Default"
                    else os.path.join(settings.PIPER_VOICES_DIR, voice_id)
                )
                self.tts_engine = engine_class(
                    output_devices=selected_devices,
                    model_path=voice_to_use,
                    playback_speed=playback_speed,
                    volume=volume,
                )

            self.current_engine_id = engine_id

            num_devices = len(selected_devices)
            plural = "" if num_devices == 1 else "s"
            device_count_str = f"{num_devices} device{plural}"
            speed_info = f" @ {playback_speed:.1f}x" if playback_speed != 1.0 else ""
            vol_info = f" (Vol: {int(volume*100)}%)" if volume != 1.0 else ""

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
            success = self.update_engine(
                engine_id=config["engine_id"],
                selected_devices=config["selected_devices"],
                voice_id=config["voice_id"],
                sample_rate=config["sample_rate"],
                playback_speed=config["playback_speed"],
                volume=config["volume"],
            )
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

        if set(self.tts_engine.output_devices) != set(config["selected_devices"]):
            return True

        if abs(self.tts_engine.playback_speed - config["playback_speed"]) > 0.01:
            return True

        if abs(self.tts_engine.volume - config["volume"]) > 0.01:
            return True

        # Engine-specific checks
        if self.current_engine_id == "say":
            voice_to_check = (
                None if config["voice_id"] == "Default" else config["voice_id"]
            )
            if getattr(self.tts_engine, "voice", None) != voice_to_check:
                return True
        elif self.current_engine_id == "bark":
            voice_to_check = (
                settings.DEFAULT_BARK_SPEAKER
                if config["voice_id"] == "Default"
                else config["voice_id"]
            )
            if (
                getattr(self.tts_engine, "voice_preset", None) != voice_to_check
                or getattr(self.tts_engine, "sample_rate", None)
                != config["sample_rate"]
            ):
                return True
        elif self.current_engine_id == "piper":
            voice_to_check = (
                settings.PIPER_MODEL_PATH
                if config["voice_id"] == "Default"
                else os.path.join(settings.PIPER_VOICES_DIR, config["voice_id"])
            )
            if getattr(self.tts_engine, "model_path", None) != voice_to_check:
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
                    self.set_status(f"Exported to {os.path.basename(output_path)}")
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
