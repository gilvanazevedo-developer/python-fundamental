"""
Integration tests for the Phase 9 language-switch infrastructure:

  - src/ui/i18n._() shorthand
  - src.services.translation_service.get_current_language()
  - src.ui.mixins.i18n_mixin.I18nMixin observer lifecycle
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock, call

import pytest

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import src.services.translation_service as ts
from src.ui.i18n import _, ngettext
from src.ui.mixins.i18n_mixin import I18nMixin


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def reset_ts():
    ts._reset()
    yield
    ts._reset()


# ---------------------------------------------------------------------------
# 1. _() shorthand delegates to current locale
# ---------------------------------------------------------------------------

class TestUnderscoreHelper:

    def test_default_english(self):
        assert _("Dashboard") == "Dashboard"

    def test_pt_BR_after_switch(self):
        ts.switch_language("pt_BR")
        assert _("Dashboard") == "Painel de Controle"

    def test_es_after_switch(self):
        ts.switch_language("es")
        assert _("Dashboard") == "Panel de Control"

    def test_back_to_english(self):
        ts.switch_language("pt_BR")
        ts.switch_language("en")
        assert _("Dashboard") == "Dashboard"

    def test_ngettext_plural(self):
        ts.switch_language("en")
        assert ngettext("%(n)d alert", "%(n)d alerts", 2) == "%(n)d alerts"


# ---------------------------------------------------------------------------
# 2. get_current_language() reflects the active locale
# ---------------------------------------------------------------------------

class TestGetCurrentLanguage:

    def test_default_is_en(self):
        assert ts.get_current_language() == "en"

    def test_reflects_pt_BR_switch(self):
        ts.switch_language("pt_BR")
        assert ts.get_current_language() == "pt_BR"

    def test_reflects_es_switch(self):
        ts.switch_language("es")
        assert ts.get_current_language() == "es"


# ---------------------------------------------------------------------------
# 3. I18nMixin — observer registered by enable_i18n()
# ---------------------------------------------------------------------------

class TestI18nMixinRegistered:

    def test_observer_in_list_after_enable(self):
        mixin = I18nMixin()
        mixin.enable_i18n()
        assert mixin._on_language_changed in ts._observers
        ts.unsubscribe(mixin._on_language_changed)  # cleanup


# ---------------------------------------------------------------------------
# 4. I18nMixin — observer removed by disable_i18n()
# ---------------------------------------------------------------------------

class TestI18nMixinDeregistered:

    def test_observer_removed_after_disable(self):
        mixin = I18nMixin()
        mixin.enable_i18n()
        mixin.disable_i18n()
        assert mixin._on_language_changed not in ts._observers


# ---------------------------------------------------------------------------
# 5. I18nMixin — update_language() is called when language switches
# ---------------------------------------------------------------------------

class TestI18nMixinRefreshOnSwitch:

    def test_update_language_called_on_switch(self):
        """_on_language_changed() must call update_language() via _refresh_labels()."""

        class MockView(I18nMixin):
            def __init__(self):
                self.update_language = MagicMock()

        view = MockView()
        view.enable_i18n()

        ts.switch_language("pt_BR")

        view.update_language.assert_called_once()
        view.disable_i18n()

    def test_update_language_not_called_after_disable(self):
        class MockView(I18nMixin):
            def __init__(self):
                self.update_language = MagicMock()

        view = MockView()
        view.enable_i18n()
        view.disable_i18n()

        ts.switch_language("es")

        view.update_language.assert_not_called()
