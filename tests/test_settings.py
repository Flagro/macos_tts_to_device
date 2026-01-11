"""Tests for settings module."""

import settings


def test_default_settings_values():
    """Test that default settings have expected values."""
    assert settings.DEFAULT_ENGINE in ["say", "bark"]
    assert isinstance(settings.WINDOW_WIDTH, int)
    assert isinstance(settings.WINDOW_HEIGHT, int)
    assert settings.WINDOW_WIDTH > 0
    assert settings.WINDOW_HEIGHT > 0


def test_bark_voices_structure():
    """Test that BARK_VOICES dictionary is properly structured."""
    assert isinstance(settings.BARK_VOICES, dict)
    assert len(settings.BARK_VOICES) > 0

    # Check that all voice IDs follow expected format
    for voice_id, description in settings.BARK_VOICES.items():
        assert "/" in voice_id, f"Voice ID {voice_id} should contain '/'"
        assert voice_id.startswith(
            "v2/"
        ), f"Voice ID {voice_id} should start with 'v2/'"
        assert isinstance(description, str)


def test_sample_rate_configuration():
    """Test sample rate settings are valid."""
    assert settings.DEFAULT_SAMPLE_RATE in settings.AVAILABLE_SAMPLE_RATES
    assert all(
        int(rate) > 0 for rate in settings.AVAILABLE_SAMPLE_RATES
    ), "All sample rates should be positive integers"
