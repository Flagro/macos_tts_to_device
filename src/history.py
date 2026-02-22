import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional, Union
import settings

logger = logging.getLogger(__name__)


class HistoryManager:
    """Manages recording and retrieval of spoken text history."""

    def __init__(self, history_file: Union[str, Path] = settings.HISTORY_FILE):
        self.history_file = Path(history_file)
        self.max_items = settings.MAX_HISTORY_ITEMS
        self.history: List[Dict[str, Any]] = self._load_history()

    def _load_history(self) -> List[Dict[str, Any]]:
        """Load history from the JSON file."""
        if not self.history_file.exists():
            return []
        try:
            with self.history_file.open("r", encoding="utf-8") as f:
                data = json.load(f)
                return data if isinstance(data, list) else []
        except (json.JSONDecodeError, ValueError) as e:
            logger.error(f"History file corrupted: {e}. Starting fresh.")
            return []
        except Exception as e:
            logger.error(f"Failed to load history: {e}")
            return []

    def add_entry(
        self,
        text: str,
        engine_id: str,
        voice: str,
        speed: float,
        devices: List[str],
        volume: float = 1.0,
        sample_rate: Optional[str] = None,
    ) -> None:
        """Add a new entry to the history."""
        entry = {
            "timestamp": datetime.now().isoformat(),
            "text": text,
            "engine": engine_id,
            "voice": voice,
            "speed": speed,
            "volume": volume,
            "devices": devices,
            "sample_rate": sample_rate,
        }

        # Add to the beginning of the list
        self.history.insert(0, entry)

        # Trim if necessary
        if len(self.history) > self.max_items:
            self.history = self.history[: self.max_items]

        self._save_history()

    def _save_history(self) -> None:
        """Save history to the JSON file."""
        try:
            with self.history_file.open("w", encoding="utf-8") as f:
                json.dump(self.history, f, indent=4)
        except Exception as e:
            logger.error(f"Failed to save history: {e}")

    def get_history(self) -> List[Dict[str, Any]]:
        """Return the current history."""
        return self.history

    def clear_history(self) -> None:
        """Clear all history."""
        self.history = []
        self._save_history()

    def delete_entry(self, index: int) -> bool:
        """Delete a single history entry by index."""
        if 0 <= index < len(self.history):
            self.history.pop(index)
            self._save_history()
            return True
        return False
