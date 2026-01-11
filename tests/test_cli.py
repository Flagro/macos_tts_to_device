"""Tests for CLI interface."""

from unittest.mock import patch, MagicMock
from click.testing import CliRunner

import pytest

from cli import main


def test_cli_help():
    """Test that CLI help text is displayed correctly."""
    runner = CliRunner()
    result = runner.invoke(main, ["--help"])
    assert result.exit_code == 0
    assert "Route TTS audio to specific output devices" in result.output
    assert "--engine" in result.output
    assert "--devices" in result.output


def test_cli_list_voices_say():
    """Test listing voices for say engine."""
    runner = CliRunner()

    # Mock list_available_voices to avoid calling actual 'say' command
    with patch("src.tts_say.SayTTSEngine.print_available_voices") as mock_print:
        result = runner.invoke(main, ["--engine", "say", "--list-voices"])

        assert result.exit_code == 0
        mock_print.assert_called_once()


def test_cli_speak_text_with_say_engine():
    """Test speaking text with say engine via CLI."""
    runner = CliRunner()

    # Mock SayTTSEngine to avoid actual TTS
    with patch("cli.SayTTSEngine") as MockEngine:
        mock_instance = MagicMock()
        MockEngine.return_value = mock_instance

        result = runner.invoke(
            main,
            [
                "--engine",
                "say",
                "--devices",
                "TestDevice",
                "--text",
                "Hello world",
            ],
        )

        assert result.exit_code == 0
        # Verify engine was initialized
        MockEngine.assert_called_once()
        # Verify process_text was called with the text
        mock_instance.process_text.assert_called_once_with("Hello world")
