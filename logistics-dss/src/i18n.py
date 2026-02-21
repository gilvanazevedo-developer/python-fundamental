"""
Internationalisation (i18n) helper.

Thin singleton that loads a JSON locale file and exposes:
    t(key)            — look up a translation string (falls back to key)
    set_language(lang)— switch the active locale ("en", "pt", "es")
    get_language()    — return the current locale code
"""

import json
from pathlib import Path

_LOCALES_DIR = Path(__file__).parent.parent / "config" / "locales"
_DEFAULT_LANG = "en"


class _Translator:
    """Singleton translator that loads and caches locale JSON."""

    _instance: "_Translator | None" = None
    _translations: dict = {}
    _language: str = _DEFAULT_LANG

    # ------------------------------------------------------------------ #
    # Singleton access                                                     #
    # ------------------------------------------------------------------ #

    @classmethod
    def instance(cls) -> "_Translator":
        if cls._instance is None:
            cls._instance = cls()
            cls._instance._load(_DEFAULT_LANG)
        return cls._instance

    # ------------------------------------------------------------------ #
    # Public helpers                                                       #
    # ------------------------------------------------------------------ #

    def _load(self, lang: str) -> None:
        """Load the locale file for *lang*; fall back to English on missing file."""
        path = _LOCALES_DIR / f"{lang}.json"
        if not path.exists():
            path = _LOCALES_DIR / "en.json"
            lang = "en"
        with open(path, "r", encoding="utf-8") as fh:
            self._translations = json.load(fh)
        self._language = lang

    def translate(self, key: str) -> str:
        """Return the translation for *key*, or *key* itself if not found."""
        return self._translations.get(key, key)

    def language(self) -> str:
        return self._language


# --------------------------------------------------------------------------- #
# Module-level convenience API                                                 #
# --------------------------------------------------------------------------- #

def set_language(lang: str) -> None:
    """Switch the active locale.  ``lang`` must be one of "en", "pt", "es"."""
    _Translator.instance()._load(lang)


def get_language() -> str:
    """Return the currently active locale code ("en", "pt", or "es")."""
    return _Translator.instance().language()


def t(key: str) -> str:
    """Return the translation of *key* in the current locale."""
    return _Translator.instance().translate(key)
