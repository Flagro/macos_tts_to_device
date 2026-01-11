"""Tests for TTSEngine base class."""

import os
import tempfile
import threading
from unittest.mock import Mock, patch, MagicMock

import pytest
import sounddevice as sd

from src.tts_base import TTSEngine


class ConcreteTTSEngine(TTSEngine):
    """Concrete implementation for testing."""

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
    def print_available_voices():
        print("Test Voice 1")
        print("Test Voice 2")


def test_tts_engine_initialization():
    """Test that TTSEngine initializes with correct parameters."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        engine = ConcreteTTSEngine(output_devices=["Test Device"], tmp_dir=tmp_dir)
        assert engine.output_devices == ["Test Device"]
        assert engine.tmp_dir == tmp_dir
        assert os.path.exists(tmp_dir)


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
            files = os.listdir(tmp_dir)
            assert len(files) == 0, "Temporary file should be cleaned up"
