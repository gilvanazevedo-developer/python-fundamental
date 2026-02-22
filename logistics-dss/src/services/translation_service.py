"""
TranslationService — runtime locale switching with observer notification.

Usage:
    from src.services import translation_service as ts

    ts.switch_language("pt_BR")        # loads pt_BR .mo; notifies all observers
    ts.switch_language("en")           # revert to English
    ts.translate("Dashboard")          # → "Painel de Controle" (when pt_BR active)
"""

import gettext
import logging
from pathlib import Path
from typing import Callable

from config.constants import (
    I18N_DOMAIN,
    LOCALE_DIR,
    LANGUAGE_TO_I18N_CODE,
    DEFAULT_LANGUAGE,
)

_logger = logging.getLogger(__name__)

# Active GNUTranslations object; NullTranslations returns msgid unchanged (EN fallback)
_current: gettext.NullTranslations = gettext.NullTranslations()
_current_lang: str = DEFAULT_LANGUAGE
_observers: list[Callable[[str], None]] = []

# Resolve locale/ directory relative to repo root (works in dev and PyInstaller bundle)
_LOCALE_DIR = Path(__file__).parent.parent.parent / LOCALE_DIR


def switch_language(lang: str) -> None:
    """Load the .mo file for `lang` and notify all registered view callbacks.

    Falls back silently to English (NullTranslations) if the locale file is absent.
    Also updates the legacy JSON-based src.i18n translator so views using t() stay
    in sync with the gettext system.
    """
    global _current, _current_lang
    try:
        t = gettext.translation(I18N_DOMAIN, localedir=str(_LOCALE_DIR), languages=[lang])
        _current = t
        _current_lang = lang
        _logger.info("Language switched to '%s'", lang)
    except FileNotFoundError:
        _current = gettext.NullTranslations()
        _current_lang = DEFAULT_LANGUAGE
        _logger.warning(
            "Locale file for '%s' not found; falling back to English.", lang
        )

    # Keep the legacy JSON-based translator in sync
    try:
        from src.i18n import set_language as _set_json_lang
        json_code = LANGUAGE_TO_I18N_CODE.get(_current_lang, "en")
        _set_json_lang(json_code)
    except Exception:
        pass

    for callback in list(_observers):
        try:
            callback(_current_lang)
        except Exception:
            _logger.exception("Observer callback raised during language switch.")


def get_current_language() -> str:
    """Return the active locale code ('en', 'pt_BR', 'es')."""
    return _current_lang


def translate(text: str) -> str:
    """Return the translation of `text` in the current locale.

    Returns `text` unchanged if no translation is found (English fallback).
    """
    return _current.gettext(text)


def ntranslate(singular: str, plural: str, n: int) -> str:
    """Return the plural-correct translation for `n` items."""
    return _current.ngettext(singular, plural, n)


def subscribe(callback: Callable[[str], None]) -> None:
    """Register a callable to be notified on every switch_language() call."""
    if callback not in _observers:
        _observers.append(callback)


def unsubscribe(callback: Callable[[str], None]) -> None:
    """Remove a previously registered observer."""
    if callback in _observers:
        _observers.remove(callback)


def _reset() -> None:
    """Reset module state to defaults — used by tests to isolate state."""
    global _current, _current_lang, _observers
    _current = gettext.NullTranslations()
    _current_lang = DEFAULT_LANGUAGE
    _observers = []
