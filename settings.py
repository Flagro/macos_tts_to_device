"""
Application settings and default values.
"""

# Window Configuration
WINDOW_WIDTH = 600
WINDOW_HEIGHT = 500
WINDOW_TITLE = "macOS TTS to Device"

# Default Engine
DEFAULT_ENGINE = "say"

# Audio Configuration
DEFAULT_SAMPLE_RATE = "24000"
AVAILABLE_SAMPLE_RATES = ["16000", "22050", "24000", "44100", "48000"]
PREFERRED_DEFAULT_DEVICE = "BlackHole 16ch"

# Voice/Speaker Defaults
DEFAULT_BARK_SPEAKER = "v2/en_speaker_6"
DEFAULT_SAY_VOICE = ""  # Empty string means system default

# Engine Configuration
SAY_ENGINE_TIMEOUT = 30

# UI Configuration
TEXT_INPUT_HEIGHT = 10
TEXT_INPUT_WIDTH = 50
TEXT_INPUT_FONT_SIZE = 11
HELP_TEXT_FONT_SIZE = 9

# Help Text
VOICE_HELP_SAY = "(Optional) e.g., 'Alex', 'Samantha' - leave empty for default"
VOICE_HELP_BARK = "(Optional) e.g., 'v2/en_speaker_6' - leave empty for default"

# Engine Metadata
ENGINE_METADATA = {
    "say": {
        "name": "macOS Say (Fast)",
        "supports_sample_rate": False,
    },
    "bark": {
        "name": "Bark AI (Natural)",
        "supports_sample_rate": True,
    },
}

# Logging Configuration
LOG_LEVEL = "WARNING"
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
