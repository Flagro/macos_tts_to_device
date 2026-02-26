"""Tests for TTSEngine base class."""

import tempfile
import threading
from pathlib import Path
from unittest.mock import patch, MagicMock
from io import StringIO
from typing import Any

import numpy as np
import pytest

from src.tts_base import TTSEngine


class ConcreteTTSEngine(TTSEngine):
    """Concrete implementation for testing."""

    @classmethod
    def from_config(cls, config: dict[str, Any]) -> "ConcreteTTSEngine":
        return cls(
            output_devices=config.get("selected_devices", []),
            tmp_dir=config.get("tmp_dir"),
            playback_speed=config.get("playback_speed", 1.0),
            volume=config.get("volume", 1.0),
        )

    def get_config(self) -> dict[str, Any]:
        return {
            "selected_devices": self.output_devices,
            "playback_speed": self.playback_speed,
            "volume": self.volume,
            "voice_id": getattr(self, "voice_id", "Default"),
        }

    def generate_audio(self, text: str) -> tuple[str, int]:
        """Mock audio generation."""
        audio_path = self.generate_temp_path("wav")
        # Create a dummy file
        with open(audio_path, "w") as f:
            f.write("dummy audio")
        return audio_path, 24000

    def get_engine_name(self) -> str:
        return "Test Engine"

    @staticmethod
    def list_available_voices() -> list[str]:
        return ["Voice 1", "Voice 2"]

    @staticmethod
    def print_available_voices():
        print("Test Voice 1")
        print("Test Voice 2")


def test_tts_engine_initialization():
    """Test that TTSEngine initializes with correct parameters."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        engine = ConcreteTTSEngine(output_devices=["Test Device"], tmp_dir=tmp_dir)
        assert engine.output_devices == ["Test Device"]
        assert engine.tmp_dir == Path(tmp_dir)
        assert Path(tmp_dir).exists()
        assert engine.playback_speed == 1.0


def test_tts_engine_initialization_with_playback_speed():
    """Test that TTSEngine initializes with custom playback speed."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        engine = ConcreteTTSEngine(
            output_devices=["Test Device"], tmp_dir=tmp_dir, playback_speed=1.5
        )
        assert engine.playback_speed == 1.5


def test_tts_engine_clamps_playback_speed():
    """Test that TTSEngine clamps playback speed to valid range."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        # Test too low
        engine_low = ConcreteTTSEngine(
            output_devices=["Test Device"], tmp_dir=tmp_dir, playback_speed=0.1
        )
        assert engine_low.playback_speed == 0.5

        # Test too high
        engine_high = ConcreteTTSEngine(
            output_devices=["Test Device"], tmp_dir=tmp_dir, playback_speed=5.0
        )
        assert engine_high.playback_speed == 2.0


def test_list_available_devices():
    """Test listing available audio devices."""
    with patch("sounddevice.query_devices") as mock_query:
        # Mock device list
        mock_query.return_value = [
            {
                "name": "Device 1",
                "max_output_channels": 2,
                "default_samplerate": 44100.0,
                "hostapi": 0,
            },
            {
                "name": "Input Only",
                "max_output_channels": 0,  # No output
                "default_samplerate": 44100.0,
                "hostapi": 0,
            },
            {
                "name": "Device 2",
                "max_output_channels": 8,
                "default_samplerate": 48000.0,
                "hostapi": 0,
            },
        ]

        devices = TTSEngine.list_available_devices()

        # Should only return output devices (max_output_channels > 0)
        assert len(devices) == 2
        assert devices[0]["name"] == "Device 1"
        assert devices[1]["name"] == "Device 2"


def test_process_text_rejects_text_exceeding_max_length():
    """Test that process_text raises ValueError when text exceeds MAX_TEXT_LENGTH."""
    import settings

    with tempfile.TemporaryDirectory() as tmp_dir:
        engine = ConcreteTTSEngine(output_devices=["Test Device"], tmp_dir=tmp_dir)

        with patch.object(settings, "MAX_TEXT_LENGTH", 5):
            with pytest.raises(ValueError, match="exceeds maximum length"):
                engine.process_text("This text is too long")


def test_process_text_creates_and_cleans_up_temp_file():
    """Test that process_text creates and properly cleans up temporary files."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        engine = ConcreteTTSEngine(output_devices=["Test Device"], tmp_dir=tmp_dir)

        # Mock the play_audio method to avoid actual playback
        with patch.object(engine, "play_audio") as mock_play:
            engine.process_text("Test text")

            # Verify play_audio was called
            assert mock_play.call_count == 1

            # Verify temp file was cleaned up
            files = list(Path(tmp_dir).iterdir())
            assert len(files) == 0, "Temporary file should be cleaned up"


def test_apply_speed_adjustment_no_change():
    """Test that speed adjustment with 1.0x returns original audio."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        engine = ConcreteTTSEngine(output_devices=["Test Device"], tmp_dir=tmp_dir)

        # Create test audio data
        original_data = np.random.rand(1000, 2).astype(np.float32)

        # Apply 1.0x speed (no change)
        result = engine._apply_speed_adjustment(original_data, 1.0)

        # Should return the same data
        assert np.array_equal(result, original_data)


def test_apply_speed_adjustment_faster():
    """Test that speed adjustment makes audio shorter when speed > 1.0."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        engine = ConcreteTTSEngine(output_devices=["Test Device"], tmp_dir=tmp_dir)

        # Create test audio data (1000 samples)
        original_data = np.random.rand(1000, 2).astype(np.float32)

        # Apply 2.0x speed (should be half the length)
        result = engine._apply_speed_adjustment(original_data, 2.0)

        # Result should be approximately half the length
        assert result.shape[0] == 500
        assert result.shape[1] == 2  # Channels should remain the same


def test_apply_speed_adjustment_slower():
    """Test that speed adjustment makes audio longer when speed < 1.0."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        engine = ConcreteTTSEngine(output_devices=["Test Device"], tmp_dir=tmp_dir)

        # Create test audio data (1000 samples)
        original_data = np.random.rand(1000, 2).astype(np.float32)

        # Apply 0.5x speed (should be double the length)
        result = engine._apply_speed_adjustment(original_data, 0.5)

        # Result should be approximately double the length
        assert result.shape[0] == 2000
        assert result.shape[1] == 2  # Channels should remain the same


def test_apply_speed_adjustment_mono():
    """Test that speed adjustment works with mono audio."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        engine = ConcreteTTSEngine(output_devices=["Test Device"], tmp_dir=tmp_dir)

        # Create mono audio data
        original_data = np.random.rand(1000).astype(np.float32)

        # Apply 1.5x speed
        result = engine._apply_speed_adjustment(original_data, 1.5)

        # Result should be approximately 2/3 the length
        expected_length = int(1000 / 1.5)
        assert result.shape[0] == expected_length


def test_print_available_devices():
    """Test that print_available_devices displays device information correctly."""
    with (
        patch("src.tts_base.sd.query_devices") as mock_query,
        patch("src.tts_base.sd.default") as mock_default,
        patch("sys.stdout", new_callable=StringIO) as mock_stdout,
    ):

        # Mock device list
        mock_query.return_value = [
            {
                "name": "Built-in Output",
                "max_output_channels": 2,
                "default_samplerate": 44100.0,
                "hostapi": 0,
                "index": 0,
            },
            {
                "name": "BlackHole 16ch",
                "max_output_channels": 16,
                "default_samplerate": 48000.0,
                "hostapi": 0,
                "index": 1,
            },
        ]

        # Set the device attribute of the mock to a tuple
        mock_default.device = (0, 1)

        TTSEngine.print_available_devices()

        output = mock_stdout.getvalue()

        # Verify output contains expected elements
        assert "Available Audio Output Devices" in output
        assert "Built-in Output" in output
        assert "BlackHole 16ch" in output
        assert "44100" in output
        assert "48000" in output
        assert "(default)" in output  # One device should be marked as default


def test_play_on_device_basic():
    """Test basic audio playback on a single device."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        engine = ConcreteTTSEngine(output_devices=["Test Device"], tmp_dir=tmp_dir)

        # Create a temporary audio file with actual audio data
        audio_path = str(Path(tmp_dir) / "test_audio.wav")
        test_audio = np.random.rand(1000, 2).astype(np.float32)

        with (
            patch("soundfile.read") as mock_read,
            patch("sounddevice.play") as mock_play,
            patch("sounddevice.get_stream") as mock_stream,
            patch("sounddevice.sleep"),
        ):

            # Mock reading the audio file
            mock_read.return_value = (test_audio, 24000)

            # Mock the stream to not be active (playback finished)
            mock_stream_obj = MagicMock()
            mock_stream_obj.active = False
            mock_stream.return_value = mock_stream_obj

            # Play the audio
            engine.play_on_device(audio_path, 24000, "Test Device")

            # Verify soundfile.read was called
            mock_read.assert_called_once_with(
                audio_path, dtype="float32", always_2d=True
            )

            # Verify sounddevice.play was called with correct parameters
            mock_play.assert_called_once()
            call_args = mock_play.call_args
            assert call_args[0][1] == 24000  # Sample rate
            assert call_args[1]["device"] == "Test Device"


def test_play_on_device_with_cancellation():
    """Test that play_on_device respects cancel_event."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        engine = ConcreteTTSEngine(output_devices=["Test Device"], tmp_dir=tmp_dir)

        audio_path = str(Path(tmp_dir) / "test_audio.wav")
        test_audio = np.random.rand(1000, 2).astype(np.float32)
        cancel_event = threading.Event()

        # Set cancel event before playback starts
        cancel_event.set()

        with (
            patch("soundfile.read") as mock_read,
            patch("sounddevice.play") as mock_play,
        ):

            mock_read.return_value = (test_audio, 24000)

            # Play should be cancelled immediately
            engine.play_on_device(audio_path, 24000, "Test Device", cancel_event)

            # sounddevice.play should not be called if cancelled before starting
            mock_play.assert_not_called()


def test_play_audio_multiple_devices():
    """Test playing audio on multiple devices simultaneously."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        devices = ["Device 1", "Device 2", "Device 3"]
        engine = ConcreteTTSEngine(output_devices=devices, tmp_dir=tmp_dir)

        audio_path = str(Path(tmp_dir) / "test_audio.wav")
        test_audio = np.random.rand(1000, 2).astype(np.float32)

        with patch.object(engine, "play_on_device") as mock_play_on_device:
            engine.play_audio(audio_path, 24000)

            # Verify play_on_device was called for each device
            assert mock_play_on_device.call_count == 3

            # Verify each device was used
            called_devices = [call[0][2] for call in mock_play_on_device.call_args_list]
            assert set(called_devices) == set(devices)


def test_list_available_devices_single_device():
    """Test listing devices when only a single device is returned."""
    with patch("sounddevice.query_devices") as mock_query:
        # Mock single device (not a list)
        mock_query.return_value = {
            "name": "Single Device",
            "max_output_channels": 2,
            "default_samplerate": 44100.0,
            "hostapi": 0,
        }

        devices = TTSEngine.list_available_devices()

        # Should return a list with one device
        assert len(devices) == 1
        assert devices[0]["name"] == "Single Device"
        assert devices[0]["index"] == 0


def test_list_available_devices_error_handling():
    """Test that list_available_devices handles errors appropriately."""
    with patch("sounddevice.query_devices") as mock_query:
        # Simulate an error from sounddevice
        mock_query.side_effect = RuntimeError("Audio system error")

        with pytest.raises(RuntimeError, match="Failed to query audio devices"):
            TTSEngine.list_available_devices()
