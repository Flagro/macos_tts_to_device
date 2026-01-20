"""Tests for GUI interface."""

import tkinter as tk
from unittest.mock import patch, MagicMock

import pytest

from gui import TTSApp


@pytest.fixture
def mock_tts_engines():
    """Mock TTS engine classes."""
    with patch("gui.SayTTSEngine") as mock_say, patch("gui.BarkTTSEngine") as mock_bark:
        mock_say_instance = MagicMock()
        mock_say_instance.output_devices = ["Test Device"]
        mock_say_instance.voice = None
        mock_say.return_value = mock_say_instance

        mock_bark_instance = MagicMock()
        mock_bark_instance.output_devices = ["Test Device"]
        mock_bark_instance.voice_preset = "v2/en_speaker_6"
        mock_bark_instance.sample_rate = 24000
        mock_bark.return_value = mock_bark_instance

        yield mock_say, mock_bark


def test_gui_initialization(mock_tts_engines):
    """Test that GUI initializes correctly."""
    root = tk.Tk()
    try:
        # Mock list_available_devices
        with patch("src.tts_base.TTSEngine.list_available_devices") as mock_devices:
            mock_devices.return_value = [
                {
                    "name": "Test Device",
                    "index": 0,
                    "max_output_channels": 2,
                    "default_samplerate": 44100,
                    "hostapi": 0,
                }
            ]

            # Mock list_available_voices for Say
            with patch("src.tts_say.SayTTSEngine.list_available_voices") as mock_voices:
                mock_voices.return_value = [("Alex", "en_US", "Test voice")]

                app = TTSApp(root)

                # Check that GUI components were created
                assert app.engine_var.get() == "say"
                assert len(app.available_devices) == 1
                assert "Test Device" in app.available_devices
    finally:
        root.destroy()


def test_gui_engine_switching(mock_tts_engines):
    """Test switching between TTS engines."""
    root = tk.Tk()
    try:
        with patch("src.tts_base.TTSEngine.list_available_devices") as mock_devices:
            mock_devices.return_value = [
                {
                    "name": "Test Device",
                    "index": 0,
                    "max_output_channels": 2,
                    "default_samplerate": 44100,
                    "hostapi": 0,
                }
            ]

            with patch("src.tts_say.SayTTSEngine.list_available_voices") as mock_voices:
                mock_voices.return_value = [("Alex", "en_US", "Test voice")]

                app = TTSApp(root)

                # Initially should be 'say'
                assert app.engine_var.get() == "say"

                # Switch to Bark
                app.engine_var.set("bark")
                app._on_engine_change()

                # Verify engine type changed
                assert app.engine_var.get() == "bark"
    finally:
        root.destroy()


def test_gui_speak_button_validation(mock_tts_engines):
    """Test that speak button validates input."""
    root = tk.Tk()
    try:
        with patch("src.tts_base.TTSEngine.list_available_devices") as mock_devices:
            mock_devices.return_value = [
                {
                    "name": "Test Device",
                    "index": 0,
                    "max_output_channels": 2,
                    "default_samplerate": 44100,
                    "hostapi": 0,
                }
            ]

            with patch("src.tts_say.SayTTSEngine.list_available_voices") as mock_voices:
                mock_voices.return_value = [("Alex", "en_US", "Test voice")]

                app = TTSApp(root)

                # Deselect all devices
                for var in app.device_vars.values():
                    var.set(False)

                # Clear text input
                app.text_input.delete("1.0", tk.END)

                # Try to speak with empty text
                app._on_speak()
                assert "enter some text" in app.status_var.get().lower()
    finally:
        root.destroy()


def test_gui_device_validation(mock_tts_engines):
    """Test that speak button validates device selection."""
    root = tk.Tk()
    try:
        with patch("src.tts_base.TTSEngine.list_available_devices") as mock_devices:
            mock_devices.return_value = [
                {
                    "name": "Test Device",
                    "index": 0,
                    "max_output_channels": 2,
                    "default_samplerate": 44100,
                    "hostapi": 0,
                }
            ]

            with patch("src.tts_say.SayTTSEngine.list_available_voices") as mock_voices:
                mock_voices.return_value = [("Alex", "en_US", "Test voice")]

                app = TTSApp(root)

                # Add text but deselect all devices
                app.text_input.insert("1.0", "Test text")
                for var in app.device_vars.values():
                    var.set(False)

                # Try to speak without device selection
                app._on_speak()
                assert (
                    "select at least one output device" in app.status_var.get().lower()
                )
    finally:
        root.destroy()


def test_gui_clear_button(mock_tts_engines):
    """Test that clear button removes text."""
    root = tk.Tk()
    try:
        with patch("src.tts_base.TTSEngine.list_available_devices") as mock_devices:
            mock_devices.return_value = [
                {
                    "name": "Test Device",
                    "index": 0,
                    "max_output_channels": 2,
                    "default_samplerate": 44100,
                    "hostapi": 0,
                }
            ]

            with patch("src.tts_say.SayTTSEngine.list_available_voices") as mock_voices:
                mock_voices.return_value = [("Alex", "en_US", "Test voice")]

                app = TTSApp(root)

                # Insert some text
                test_text = "This is test text to be cleared"
                app.text_input.insert("1.0", test_text)

                # Verify text was inserted
                assert app.text_input.get("1.0", tk.END).strip() == test_text

                # Click clear button
                app._on_clear()

                # Verify text was cleared
                assert app.text_input.get("1.0", tk.END).strip() == ""
    finally:
        root.destroy()


def test_gui_playback_speed_change(mock_tts_engines):
    """Test playback speed slider updates label."""
    root = tk.Tk()
    try:
        with patch("src.tts_base.TTSEngine.list_available_devices") as mock_devices:
            mock_devices.return_value = [
                {
                    "name": "Test Device",
                    "index": 0,
                    "max_output_channels": 2,
                    "default_samplerate": 44100,
                    "hostapi": 0,
                }
            ]

            with patch("src.tts_say.SayTTSEngine.list_available_voices") as mock_voices:
                mock_voices.return_value = [("Alex", "en_US", "Test voice")]

                app = TTSApp(root)

                # Initial speed should be 1.0
                assert app.playback_speed_var.get() == 1.0

                # Change playback speed
                app.playback_speed_var.set(1.5)
                app._on_playback_speed_change("1.5")

                # Verify label updated
                assert "1.5x" in app.playback_speed_value_label.cget("text")
    finally:
        root.destroy()


def test_gui_voice_selection(mock_tts_engines):
    """Test voice selection changes."""
    root = tk.Tk()
    try:
        mock_say_engine, _ = mock_tts_engines

        with patch("src.tts_base.TTSEngine.list_available_devices") as mock_devices:
            mock_devices.return_value = [
                {
                    "name": "Test Device",
                    "index": 0,
                    "max_output_channels": 2,
                    "default_samplerate": 44100,
                    "hostapi": 0,
                }
            ]

            # Mock the list_available_voices static method
            mock_say_engine.list_available_voices.return_value = [
                ("Alex", "en_US", "Test voice"),
                ("Samantha", "en_US", "Another voice"),
            ]

            app = TTSApp(root)

            # Verify available voices were loaded
            assert "Default" in app.available_voices
            assert "Alex" in app.available_voices
            assert "Samantha" in app.available_voices

            # Change voice selection
            app.voice_var.set("Samantha")
            assert app.voice_var.get() == "Samantha"
    finally:
        root.destroy()


def test_gui_device_refresh(mock_tts_engines):
    """Test refreshing device list."""
    root = tk.Tk()
    try:
        with patch("src.tts_base.TTSEngine.list_available_devices") as mock_devices:
            # Initial device list
            mock_devices.return_value = [
                {
                    "name": "Device 1",
                    "index": 0,
                    "max_output_channels": 2,
                    "default_samplerate": 44100,
                    "hostapi": 0,
                }
            ]

            with patch("gui.SayTTSEngine.list_available_voices") as mock_voices:
                mock_voices.return_value = [("Alex", "en_US", "Test voice")]

                app = TTSApp(root)

                # Verify initial device
                assert "Device 1" in app.available_devices
                assert len(app.available_devices) == 1

                # Update mock to return different devices
                mock_devices.return_value = [
                    {
                        "name": "Device 1",
                        "index": 0,
                        "max_output_channels": 2,
                        "default_samplerate": 44100,
                        "hostapi": 0,
                    },
                    {
                        "name": "Device 2",
                        "index": 1,
                        "max_output_channels": 2,
                        "default_samplerate": 48000,
                        "hostapi": 0,
                    },
                ]

                # Refresh devices
                app._on_refresh_devices()

                # Verify device list updated (this proves refresh worked)
                assert len(app.available_devices) == 2
                assert "Device 1" in app.available_devices
                assert "Device 2" in app.available_devices
    finally:
        root.destroy()


def test_gui_sample_rate_visibility(mock_tts_engines):
    """Test sample rate visibility based on engine."""
    root = tk.Tk()
    try:
        with patch("src.tts_base.TTSEngine.list_available_devices") as mock_devices:
            mock_devices.return_value = [
                {
                    "name": "Test Device",
                    "index": 0,
                    "max_output_channels": 2,
                    "default_samplerate": 44100,
                    "hostapi": 0,
                }
            ]

            with patch("src.tts_say.SayTTSEngine.list_available_voices") as mock_voices:
                mock_voices.return_value = [("Alex", "en_US", "Test voice")]

                app = TTSApp(root)

                # Say engine should hide sample rate
                assert app.engine_var.get() == "say"
                # Note: grid_info() returns empty dict if widget is hidden with grid_remove()
                assert not app.sample_rate_combo.grid_info()

                # Switch to Bark - sample rate should be visible
                app.engine_var.set("bark")
                app._on_engine_change()
                assert (
                    app.sample_rate_combo.grid_info()
                )  # Should have grid info when visible
    finally:
        root.destroy()
