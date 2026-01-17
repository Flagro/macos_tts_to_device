"""Tests for BarkTTSEngine."""

import tempfile
from unittest.mock import patch, MagicMock
import numpy as np

import pytest

from src.tts_bark import BarkTTSEngine


@pytest.fixture
def mock_bark_imports():
    """Mock Bark imports to avoid loading actual models."""
    # Mock the bark module first before patching its attributes
    mock_bark = MagicMock()
    mock_bark.preload_models = MagicMock(return_value=None)

    with patch.dict("sys.modules", {"bark": mock_bark}):
        yield mock_bark


def test_bark_engine_initialization(mock_bark_imports):
    """Test Bark engine initializes with correct parameters."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        engine = BarkTTSEngine(
            output_devices=["External Headphones"],
            voice_preset="v2/en_speaker_3",
            sample_rate=24000,
            tmp_dir=tmp_dir,
        )
        assert engine.output_devices == ["External Headphones"]
        assert engine.voice_preset == "v2/en_speaker_3"
        assert engine.sample_rate == 24000


def test_generate_audio_success(mock_bark_imports):
    """Test successful audio generation with Bark."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        # Mock audio output (1D numpy array)
        mock_audio = np.random.randn(24000).astype(np.float32)
        mock_bark_imports.generate_audio = MagicMock(return_value=mock_audio)

        engine = BarkTTSEngine(
            output_devices=["Test Device"],
            voice_preset="v2/en_speaker_6",
            tmp_dir=tmp_dir,
        )

        # Mock soundfile.write
        with patch("soundfile.write") as mock_write:
            audio_path, sample_rate = engine.generate_audio("Hello world")

            # Verify generate_audio was called
            mock_bark_imports.generate_audio.assert_called_once_with(
                "Hello world", history_prompt="v2/en_speaker_6"
            )

            # Verify audio was written
            mock_write.assert_called_once()
            assert audio_path.endswith(".wav")
            assert sample_rate == 24000


def test_voice_preset_validation_warning(mock_bark_imports):
    """Test that invalid voice preset triggers warning."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        with patch("src.tts_bark.logger") as mock_logger:
            engine = BarkTTSEngine(
                output_devices=["Test Device"],
                voice_preset="invalid_voice",
                tmp_dir=tmp_dir,
            )

            # Should log a warning about unknown voice
            mock_logger.warning.assert_called_once()
            assert "not in known voices list" in str(mock_logger.warning.call_args)
