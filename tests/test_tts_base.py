"""Tests for TTSEngine base class."""

import os
import tempfile
import threading
from unittest.mock import Mock, patch, MagicMock

import pytest
import numpy as np
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
