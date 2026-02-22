"""
Gettext-based i18n helpers for the UI layer.

These thin wrappers delegate to TranslationService so that individual
view modules only need a single import:

    from src.ui.i18n import _

    label.configure(text=_("Dashboard"))
"""

from src.services.translation_service import translate as _translate
from src.services.translation_service import ntranslate as _ntranslate


def _(text: str) -> str:
    """Return the gettext translation of *text* in the current locale."""
    return _translate(text)


def ngettext(singular: str, plural: str, n: int) -> str:
    """Return the plural-correct translation for *n* items."""
    return _ntranslate(singular, plural, n)
