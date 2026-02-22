"""
Unit tests for src/services/translation_service.py

Tests gettext-based locale loading, language switching, observer pattern,
plural-form support, and graceful fallback for unknown locales.
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import src.services.translation_service as ts


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def reset_service():
    """Reset module-level state before and after every test."""
    ts._reset()
    yield
    ts._reset()


# ---------------------------------------------------------------------------
# 1. Language switching — Portuguese (Brazil)
# ---------------------------------------------------------------------------

class TestSwitchToPtBR:

    def test_switch_sets_current_lang(self):
        ts.switch_language("pt_BR")
        assert ts.get_current_language() == "pt_BR"

    def test_translate_dashboard_pt_BR(self):
        ts.switch_language("pt_BR")
        assert ts.translate("Dashboard") == "Painel de Controle"

    def test_translate_inventory_pt_BR(self):
        ts.switch_language("pt_BR")
        assert ts.translate("Inventory") == "Estoque"


# ---------------------------------------------------------------------------
# 2. Language switching — Spanish
# ---------------------------------------------------------------------------

class TestSwitchToEs:

    def test_switch_sets_current_lang(self):
        ts.switch_language("es")
        assert ts.get_current_language() == "es"

    def test_translate_dashboard_es(self):
        ts.switch_language("es")
        assert ts.translate("Dashboard") == "Panel de Control"

    def test_translate_suppliers_es(self):
        ts.switch_language("es")
        assert ts.translate("Suppliers") == "Proveedores"


# ---------------------------------------------------------------------------
# 3. English is identity (msgid == msgstr)
# ---------------------------------------------------------------------------

class TestEnglishIdentity:

    def test_translate_returns_source_string(self):
        ts.switch_language("en")
        assert ts.translate("Dashboard") == "Dashboard"

    def test_current_lang_is_en_after_switch(self):
        ts.switch_language("pt_BR")
        ts.switch_language("en")
        assert ts.get_current_language() == "en"


# ---------------------------------------------------------------------------
# 4. Unknown locale falls back to English
# ---------------------------------------------------------------------------

class TestUnknownLocaleFallback:

    def test_current_lang_resets_to_default(self):
        ts.switch_language("zz_ZZ")
        assert ts.get_current_language() == "en"

    def test_translate_returns_msgid_unchanged(self):
        ts.switch_language("zz_ZZ")
        assert ts.translate("Dashboard") == "Dashboard"


# ---------------------------------------------------------------------------
# 5. Observer is called on language switch
# ---------------------------------------------------------------------------

class TestObserverCalledOnSwitch:

    def test_observer_receives_lang_code(self):
        cb = MagicMock()
        ts.subscribe(cb)
        ts.switch_language("pt_BR")
        cb.assert_called_once_with("pt_BR")

    def test_multiple_observers_all_called(self):
        cb1, cb2 = MagicMock(), MagicMock()
        ts.subscribe(cb1)
        ts.subscribe(cb2)
        ts.switch_language("es")
        cb1.assert_called_once_with("es")
        cb2.assert_called_once_with("es")


# ---------------------------------------------------------------------------
# 6. Observer NOT called after unsubscribe
# ---------------------------------------------------------------------------

class TestObserverNotCalledAfterUnsubscribe:

    def test_unsubscribed_observer_is_silent(self):
        cb = MagicMock()
        ts.subscribe(cb)
        ts.unsubscribe(cb)
        ts.switch_language("pt_BR")
        cb.assert_not_called()

    def test_unsubscribe_nonexistent_is_noop(self):
        cb = MagicMock()
        ts.unsubscribe(cb)  # should not raise


# ---------------------------------------------------------------------------
# 7. Plural forms
# ---------------------------------------------------------------------------

class TestNtranslate:

    def test_singular_english(self):
        ts.switch_language("en")
        result = ts.ntranslate("%(n)d alert", "%(n)d alerts", 1)
        assert result == "%(n)d alert"

    def test_plural_english(self):
        ts.switch_language("en")
        result = ts.ntranslate("%(n)d alert", "%(n)d alerts", 5)
        assert result == "%(n)d alerts"

    def test_singular_pt_BR(self):
        ts.switch_language("pt_BR")
        result = ts.ntranslate("%(n)d alert", "%(n)d alerts", 1)
        assert result == "%(n)d alerta"

    def test_plural_pt_BR(self):
        ts.switch_language("pt_BR")
        result = ts.ntranslate("%(n)d alert", "%(n)d alerts", 3)
        assert result == "%(n)d alertas"


# ---------------------------------------------------------------------------
# 8. All .mo files load without error
# ---------------------------------------------------------------------------

class TestAllMoFilesLoad:

    @pytest.mark.parametrize("lang", ["en", "pt_BR", "es"])
    def test_mo_loads_for_locale(self, lang):
        """switch_language() must not raise for every supported locale."""
        ts.switch_language(lang)
        assert ts.get_current_language() == lang
