"""
Settings Service
Typed settings.json I/O with default values.
Settings are persisted in config/settings.json (not the database) so that
db_path itself can be configured without a chicken-and-egg problem.
"""

import json
import sys
from pathlib import Path
from typing import Any, Optional

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from config.constants import SETTINGS_FILE_PATH, SETTINGS_DEFAULTS


class SettingsService:
    """Read and write runtime settings persisted in settings.json."""

    def __init__(self, settings_path: Optional[str] = None):
        self._path = Path(settings_path or SETTINGS_FILE_PATH)
        self._data: dict = {}
        self._load()

    # ------------------------------------------------------------------
    # I/O
    # ------------------------------------------------------------------

    def _load(self) -> None:
        """Load settings from disk; fall back to defaults if file absent."""
        defaults = dict(SETTINGS_DEFAULTS)
        if self._path.exists():
            try:
                with open(self._path, "r", encoding="utf-8") as fh:
                    on_disk = json.load(fh)
                # Merge: defaults first, then overrides from disk
                defaults.update(on_disk)
            except (json.JSONDecodeError, OSError):
                pass
        self._data = defaults

    def _save(self) -> None:
        """Persist current settings to disk."""
        self._path.parent.mkdir(parents=True, exist_ok=True)
        with open(self._path, "w", encoding="utf-8") as fh:
            json.dump(self._data, fh, indent=2)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get(self, key: str, default: Any = None) -> Any:
        """Return value for key; fall back to default if absent."""
        return self._data.get(key, default)

    def set(self, key: str, value: Any) -> None:
        """Update key in-memory and persist to disk."""
        self._data[key] = value
        self._save()

    def get_all(self) -> dict:
        """Return a copy of the full settings dict."""
        return dict(self._data)

    def reset_to_defaults(self) -> None:
        """Overwrite in-memory dict and disk with SETTINGS_DEFAULTS."""
        self._data = dict(SETTINGS_DEFAULTS)
        self._save()
