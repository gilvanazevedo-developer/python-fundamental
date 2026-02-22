"""
I18nMixin — observer-based language-change helper for CTkFrame views.

Usage::

    class MyView(ctk.CTkFrame, I18nMixin):

        def __init__(self, master, **kwargs):
            super().__init__(master, **kwargs)
            # … build widgets …
            self.enable_i18n()   # subscribe to TranslationService

        def update_language(self):
            # re-apply translated strings to all widgets
            self._some_label.configure(text=_("Dashboard"))

        def destroy(self):
            self.disable_i18n()  # unsubscribe before teardown
            super().destroy()
"""

from src.services import translation_service as _ts


class I18nMixin:
    """Mixin that subscribes a view to TranslationService language-change events."""

    def enable_i18n(self) -> None:
        """Register this view to receive language-change notifications."""
        _ts.subscribe(self._on_language_changed)

    def disable_i18n(self) -> None:
        """Unregister this view (call from ``destroy()`` to prevent memory leaks)."""
        _ts.unsubscribe(self._on_language_changed)

    def _on_language_changed(self, lang: str) -> None:
        """Callback fired by TranslationService after every ``switch_language()`` call."""
        self._refresh_labels()

    def _refresh_labels(self) -> None:
        """Re-apply translated text to all UI widgets.

        Default implementation delegates to ``update_language()`` when present.
        Subclasses may override for finer-grained control.
        """
        if hasattr(self, "update_language"):
            self.update_language()
