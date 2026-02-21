"""
Unit tests for src/i18n.py

Tests the Translator singleton, language switching, key look-up,
and fallback behaviour.
"""

import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.i18n import t, set_language, get_language


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def reset_to_english():
    """Always reset to English before and after each test."""
    set_language("en")
    yield
    set_language("en")


# ---------------------------------------------------------------------------
# Default language
# ---------------------------------------------------------------------------

class TestDefaultLanguage:

    def test_default_is_english(self):
        set_language("en")
        assert get_language() == "en"

    def test_english_nav_executive(self):
        assert t("nav.executive") == "Executive"

    def test_english_nav_dashboard(self):
        assert t("nav.dashboard") == "Dashboard"

    def test_english_common_refresh(self):
        assert t("common.refresh") == "Refresh"

    def test_english_exec_title(self):
        assert t("exec.title") == "Executive Dashboard"

    def test_english_col_sku(self):
        assert t("col.sku") == "SKU"

    def test_english_col_product(self):
        assert t("col.product") == "Product"

    def test_english_analytics_title(self):
        assert "ABC" in t("analytics.title")

    def test_english_forecast_section_chart(self):
        assert t("forecast.section.chart") == "Product Demand Forecast"

    def test_english_opt_section_summary(self):
        assert "Optimis" in t("opt.section.summary")


# ---------------------------------------------------------------------------
# Portuguese
# ---------------------------------------------------------------------------

class TestPortuguese:

    def test_language_code(self):
        set_language("pt")
        assert get_language() == "pt"

    def test_nav_executive(self):
        set_language("pt")
        assert t("nav.executive") == "Executivo"

    def test_nav_dashboard(self):
        set_language("pt")
        assert t("nav.dashboard") == "Painel"

    def test_nav_inventory(self):
        set_language("pt")
        assert t("nav.inventory") == "Estoque"

    def test_nav_analytics(self):
        set_language("pt")
        val = t("nav.analytics")
        assert "n" in val.lower()   # Análise

    def test_common_refresh(self):
        set_language("pt")
        assert t("common.refresh") == "Atualizar"

    def test_exec_title(self):
        set_language("pt")
        assert t("exec.title") == "Painel Executivo"

    def test_col_stock(self):
        set_language("pt")
        assert t("col.stock") == "Estoque"

    def test_opt_section_summary(self):
        set_language("pt")
        assert "Otimiza" in t("opt.section.summary")

    def test_forecast_kpi_critical(self):
        set_language("pt")
        assert "tico" in t("forecast.kpi.critical").lower()  # Críticos


# ---------------------------------------------------------------------------
# Spanish
# ---------------------------------------------------------------------------

class TestSpanish:

    def test_language_code(self):
        set_language("es")
        assert get_language() == "es"

    def test_nav_executive(self):
        set_language("es")
        assert t("nav.executive") == "Ejecutivo"

    def test_nav_dashboard(self):
        set_language("es")
        assert t("nav.dashboard") == "Panel"

    def test_nav_inventory(self):
        set_language("es")
        assert t("nav.inventory") == "Inventario"

    def test_common_refresh(self):
        set_language("es")
        assert t("common.refresh") == "Actualizar"

    def test_exec_title(self):
        set_language("es")
        assert t("exec.title") == "Panel Ejecutivo"

    def test_col_stock(self):
        set_language("es")
        assert t("col.stock") == "Stock"

    def test_col_category(self):
        set_language("es")
        assert "Categor" in t("col.category")

    def test_opt_section_summary(self):
        set_language("es")
        assert "Optimizaci" in t("opt.section.summary")

    def test_forecast_kpi_no_demand(self):
        set_language("es")
        assert "Demanda" in t("forecast.kpi.no_demand")


# ---------------------------------------------------------------------------
# Language switching
# ---------------------------------------------------------------------------

class TestLanguageSwitching:

    def test_switch_en_to_pt_to_es(self):
        set_language("en")
        assert t("nav.dashboard") == "Dashboard"

        set_language("pt")
        assert t("nav.dashboard") == "Painel"

        set_language("es")
        assert t("nav.dashboard") == "Panel"

    def test_switch_back_to_english(self):
        set_language("pt")
        set_language("en")
        assert t("nav.dashboard") == "Dashboard"
        assert get_language() == "en"

    def test_multiple_calls_same_language(self):
        set_language("pt")
        set_language("pt")
        assert get_language() == "pt"
        assert t("common.refresh") == "Atualizar"


# ---------------------------------------------------------------------------
# Fallback behaviour
# ---------------------------------------------------------------------------

class TestFallback:

    def test_missing_key_returns_key(self):
        result = t("this.key.does.not.exist")
        assert result == "this.key.does.not.exist"

    def test_empty_string_key(self):
        result = t("")
        assert result == ""

    def test_unknown_language_falls_back_to_english(self):
        set_language("xx")   # non-existent locale → falls back to en.json
        assert t("nav.executive") == "Executive"
        assert get_language() == "en"


# ---------------------------------------------------------------------------
# Coverage: all required top-level key groups exist
# ---------------------------------------------------------------------------

class TestRequiredKeys:

    REQUIRED = [
        "app.title", "app.appearance", "app.language",
        "nav.executive", "nav.dashboard", "nav.inventory",
        "nav.analytics", "nav.forecasting", "nav.optimization", "nav.import",
        "common.refresh", "common.category", "common.period",
        "common.history_days", "common.horizon_days", "common.method",
        "common.export_excel", "common.export_csv",
        "col.sku", "col.product", "col.category", "col.stock",
        "col.status", "col.days_left", "col.rop", "col.eoq",
        "exec.title", "exec.kpi.revenue", "exec.kpi.fill_rate",
        "exec.section.alerts", "exec.section.savings", "exec.section.top_products",
        "dash.kpi.total_skus", "dash.section.alerts",
        "inv.detail.placeholder",
        "analytics.title", "analytics.class.a", "analytics.class.b", "analytics.class.c",
        "forecast.section.overview", "forecast.kpi.critical",
        "opt.section.summary", "opt.section.detail", "opt.kpi.savings",
    ]

    @pytest.mark.parametrize("lang", ["en", "pt", "es"])
    def test_all_required_keys_present(self, lang):
        set_language(lang)
        for key in self.REQUIRED:
            result = t(key)
            assert result != key, f"Key '{key}' missing in locale '{lang}'"
