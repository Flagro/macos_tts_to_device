"""macOS 'say' command TTS engine implementation."""

import logging
import subprocess
from typing import Optional

import soundfile as sf

from ..tts_base import TTSEngine

logger = logging.getLogger(__name__)


@TTSEngine.register("say")
class SayTTSEngine(TTSEngine):
    """TTS engine using macOS built-in 'say' command."""

    display_name = "macOS Say (Fast)"
    supports_sample_rate = False

    def __init__(
        self,
        output_devices: list[str],
        voice: Optional[str] = None,
        tmp_dir: Optional[str] = None,
        timeout: int = 30,
        playback_speed: float = 1.0,
        volume: float = 1.0,
        voice_id: str = "Default",
    ):
        """
        Initialize the Say TTS engine.

        Args:
            output_devices: List of output device names or IDs
            voice: macOS voice name (e.g., "Alex", "Samantha"), None for default
            tmp_dir: Directory for temporary audio files
            timeout: Timeout in seconds for the 'say' command (default: 30)
            playback_speed: Playback speed multiplier (0.5-2.0, default: 1.0)
            volume: Volume multiplier (0.0-1.0, default: 1.0)
            voice_id: The requested voice ID
        """
        super().__init__(output_devices, tmp_dir, playback_speed, volume, voice_id)
        self.voice = voice
        self.timeout = timeout
        logger.info(
            f"Initialized SayTTSEngine with voice='{voice}', timeout={timeout}s, devices={output_devices}"
        )

    @classmethod
    def from_config(cls, config: dict[str, Any]) -> "SayTTSEngine":
        """Create a SayTTSEngine instance from configuration."""
        import settings

        voice_id = config.get("voice_id", "Default")
        # Handle "Default" option (use system default voice)
        voice_to_use = None if voice_id == "Default" else voice_id

        return cls(
            output_devices=config.get("selected_devices", []),
            voice=voice_to_use,
            timeout=settings.SAY_ENGINE_TIMEOUT,
            playback_speed=config.get("playback_speed", 1.0),
            volume=config.get("volume", 1.0),
            tmp_dir=config.get("tmp_dir"),
            voice_id=voice_id,
        )

    def get_config(self) -> dict[str, Any]:
        """Return current configuration."""
        return {
            "engine_id": "say",
            "selected_devices": self.output_devices,
            "voice_id": self.voice_id,
            "playback_speed": self.playback_speed,
            "volume": self.volume,
            "sample_rate": 0,  # Not supported
        }

    def generate_audio(self, text: str) -> tuple[str, int]:
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
            subprocess.run(
                cmd, check=True, capture_output=True, text=True, timeout=self.timeout
            )
            logger.info(f"Successfully generated audio file: {audio_path}")
        except subprocess.TimeoutExpired as e:
            logger.error(
                f"Command timed out after {self.timeout} seconds: {' '.join(cmd)}"
            )
            raise RuntimeError(
                f"The 'say' command timed out after {self.timeout} seconds. Text may be too long."
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

    supports_sample_rate = False

    def _print_engine_specific_info(self):
        """Print Say-specific configuration info."""
        if self.voice:
            print(f"Voice: {self.voice}")
        else:
            print("Voice: Default")

    @staticmethod
    def list_available_voices() -> list[dict[str, str]]:
        """
        Get a list of available voices from the 'say' command.

        Returns:
            List of dictionaries containing {"id": voice_name, "name": display_name}
        """
        try:
            result = subprocess.run(
                ["say", "-v", "?"],
                check=True,
                capture_output=True,
                text=True,
                timeout=5,
            )
            voices = []
            for line in result.stdout.strip().split("\n"):
                if line.strip():
                    # Format: "VoiceName    language_CODE    # Description"
                    parts = line.split("#", 1)
                    voice_info = parts[0].strip().split()
                    if len(voice_info) >= 2:
                        voice_name = voice_info[0]
                        lang = voice_info[1]
                        desc = parts[1].strip() if len(parts) == 2 else ""
                        display_name = f"{voice_name} ({lang})"
                        if desc:
                            display_name += f" - {desc}"
                        voices.append({"id": voice_name, "name": display_name})
            logger.info(f"Found {len(voices)} available voices")
            return voices
        except subprocess.TimeoutExpired as e:
            logger.error("Command 'say -v ?' timed out")
            raise RuntimeError("Failed to list voices: command timed out") from e
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to list voices: {e.stderr}")
            raise RuntimeError(f"Failed to list voices: {e.stderr}") from e
        except FileNotFoundError as e:
            logger.error("'say' command not found")
            raise RuntimeError(
                "The 'say' command was not found. This tool requires macOS."
            ) from e

    @staticmethod
    def print_available_voices():
        """Print a formatted list of available voices."""
        voices = SayTTSEngine.list_available_voices()
        print(f"\nAvailable voices ({len(voices)} total):\n")
        print(f"{'Voice ID':<20} Display Name")
        print("-" * 60)
        for voice in voices:
            print(f"{voice['id']:<20} {voice['name']}")
