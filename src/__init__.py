"""TTS to Device implementations."""

from .tts_base import TTSEngine
from .engines import load_engines
from .profiles import ProfileManager
from .history import HistoryManager

# Pre-load engines so they are registered when src is imported
load_engines()


# For backward compatibility, though using TTSEngine.get_engine_class() is preferred
def _get_engine_safe(engine_id):
    try:
        return TTSEngine.get_engine_class(engine_id)
    except ValueError:
        return None


SayTTSEngine = _get_engine_safe("say")
BarkTTSEngine = _get_engine_safe("bark")

__all__ = [
    "TTSEngine",
    "load_engines",
    "SayTTSEngine",
    "BarkTTSEngine",
    "ProfileManager",
    "HistoryManager",
]
