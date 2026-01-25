"""Tests for SayTTSEngine."""

import tempfile
from unittest.mock import patch, MagicMock
import subprocess

import pytest

from src.engines.say import SayTTSEngine


def test_say_engine_initialization():
    """Test Say engine initializes with correct parameters."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        engine = SayTTSEngine(
            output_devices=["BlackHole 16ch"],
            voice="Alex",
            tmp_dir=tmp_dir,
            timeout=15,
        )
        assert engine.output_devices == ["BlackHole 16ch"]
        assert engine.voice == "Alex"
        assert engine.timeout == 15


def test_generate_audio_success():
    """Test successful audio generation with say command."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        engine = SayTTSEngine(
            output_devices=["Test Device"], voice="Alex", tmp_dir=tmp_dir
        )

        # Mock subprocess.run to simulate successful 'say' command
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

            # Mock soundfile.info to return sample rate
            with patch("soundfile.info") as mock_info:
                mock_info.return_value = MagicMock(
                    samplerate=22050, channels=1, duration=1.5
                )

                audio_path, sample_rate = engine.generate_audio("Hello world")

                # Verify 'say' command was called with correct arguments
                mock_run.assert_called_once()
                call_args = mock_run.call_args[0][0]
                assert call_args[0] == "say"
                assert "-v" in call_args
                assert "Alex" in call_args
                assert "Hello world" in call_args

                # Verify return values
                assert audio_path.endswith(".aiff")
                assert sample_rate == 22050


def test_generate_audio_timeout():
    """Test that timeout is properly handled."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        engine = SayTTSEngine(
            output_devices=["Test Device"], timeout=5, tmp_dir=tmp_dir
        )

        # Mock subprocess.run to raise TimeoutExpired
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = subprocess.TimeoutExpired(cmd=["say"], timeout=5)

            with pytest.raises(RuntimeError, match="timed out"):
                engine.generate_audio("Test text")
