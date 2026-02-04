import json
import os
import logging
from typing import Dict, Any, List, Optional
import settings

logger = logging.getLogger(__name__)


class ProfileManager:
    """Manages saving and loading of TTS configuration profiles."""

    def __init__(self, profiles_file: str = settings.PROFILES_FILE):
        self.profiles_file = profiles_file
        self.profiles: Dict[str, Any] = self._load_profiles()

    def _load_profiles(self) -> Dict[str, Any]:
        """Load profiles from the JSON file."""
        if not os.path.exists(self.profiles_file):
            return {}
        try:
            with open(self.profiles_file, "r") as f:
                data = json.load(f)
                return data if isinstance(data, dict) else {}
        except (json.JSONDecodeError, ValueError) as e:
            logger.error(f"Profiles file corrupted: {e}. Starting fresh.")
            return {}
        except Exception as e:
            logger.error(f"Failed to load profiles: {e}")
            return {}

    def save_profile(self, name: str, settings_dict: Dict[str, Any]) -> bool:
        """Save a new profile or update an existing one."""
        self.profiles[name] = settings_dict
        try:
            with open(self.profiles_file, "w") as f:
                json.dump(self.profiles, f, indent=4)
            return True
        except Exception as e:
            logger.error(f"Failed to save profile '{name}': {e}")
            return False

    def delete_profile(self, name: str) -> bool:
        """Delete a profile by name."""
        if name in self.profiles:
            del self.profiles[name]
            try:
                with open(self.profiles_file, "w") as f:
                    json.dump(self.profiles, f, indent=4)
                return True
            except Exception as e:
                logger.error(f"Failed to delete profile '{name}': {e}")
                return False
        return False

    def get_profile(self, name: str) -> Optional[Dict[str, Any]]:
        """Get profile settings by name."""
        return self.profiles.get(name)

    def list_profiles(self) -> List[str]:
        """List all available profile names."""
        return sorted(list(self.profiles.keys()))
