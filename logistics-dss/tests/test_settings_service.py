"""
Unit tests for src/services/settings_service.py (T8-28)
6 tests covering get, set, persistence, defaults, reset, and missing keys.
"""

import json
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.services.settings_service import SettingsService
from config.constants import SETTINGS_DEFAULTS


@pytest.fixture
def settings_file(tmp_path):
    """Path to a temporary settings.json (not yet written)."""
    return str(tmp_path / "settings.json")


@pytest.fixture
def settings(settings_file):
    """SettingsService backed by a temporary file."""
    return SettingsService(settings_path=settings_file)


class TestSettingsService:

    def test_get_default_log_level(self, settings_file):
        """settings.json absent → get('log_level', 'INFO') returns 'INFO'."""
        svc = SettingsService(settings_path=settings_file)
        # file doesn't exist yet → should fall back to defaults
        assert svc.get("log_level", "INFO") == "INFO"

    def test_set_and_get(self, settings):
        """set('theme', 'light'); get('theme') returns 'light'."""
        settings.set("theme", "light")
        assert settings.get("theme") == "light"

    def test_set_persists_to_file(self, settings, settings_file):
        """After set(), reading settings.json directly confirms the value was written."""
        settings.set("theme", "light")
        with open(settings_file, "r") as fh:
            on_disk = json.load(fh)
        assert on_disk.get("theme") == "light"

    def test_get_all_returns_all_default_keys(self, settings):
        """get_all() dict contains all SETTINGS_DEFAULTS keys."""
        all_settings = settings.get_all()
        for key in SETTINGS_DEFAULTS:
            assert key in all_settings, f"Key '{key}' missing from get_all()"

    def test_reset_to_defaults(self, settings):
        """After set('theme', 'light'), reset_to_defaults() → get('theme') returns 'dark'."""
        settings.set("theme", "light")
        assert settings.get("theme") == "light"
        settings.reset_to_defaults()
        assert settings.get("theme") == SETTINGS_DEFAULTS["theme"]

    def test_invalid_key_returns_default(self, settings):
        """get('nonexistent', 'fallback') returns 'fallback' without error."""
        result = settings.get("nonexistent_key_xyz", "fallback")
        assert result == "fallback"
