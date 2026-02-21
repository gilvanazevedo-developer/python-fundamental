"""
Integration tests for src/services/forecast_service.py

Uses a clean in-memory SQLite database via the clean_database fixture.
"""

import sys
from pathlib import Path
from datetime import date, timedelta
from decimal import Decimal

import pytest

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.services.forecast_service import ForecastService
from src.database.models import Product, Warehouse, InventoryLevel, SalesRecord


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _seed_products(db_manager):
    """Seed two products with 30 days of daily sales and inventory."""
    today = date.today()
    with db_manager.get_session() as session:
        session.add(Product(id="SKU-1", name="Steady Seller", category="Cat1",
                            unit_cost=Decimal("5"), unit_price=Decimal("10")))
        session.add(Product(id="SKU-2", name="Slow Mover", category="Cat2",
                            unit_cost=Decimal("3"), unit_price=Decimal("6")))
        session.add(Warehouse(id="WH1", name="Main", location="City", capacity=5000))

        # SKU-1: 10 units/day for 30 days → predictable demand
        for offset in range(1, 31):
            session.add(SalesRecord(
                date=today - timedelta(days=offset),
                product_id="SKU-1",
                warehouse_id="WH1",
                quantity_sold=10,
                revenue=Decimal("100"),
            ))

        # SKU-2: 2 units/day for 30 days
        for offset in range(1, 31):
            session.add(SalesRecord(
                date=today - timedelta(days=offset),
                product_id="SKU-2",
                warehouse_id="WH1",
                quantity_sold=2,
                revenue=Decimal("12"),
            ))

        # Inventory: SKU-1 has low stock (5 days of supply), SKU-2 comfortable
        session.add(InventoryLevel(product_id="SKU-1", warehouse_id="WH1", quantity=50))
        session.add(InventoryLevel(product_id="SKU-2", warehouse_id="WH1", quantity=200))

        session.commit()


# ---------------------------------------------------------------------------
# get_product_forecast
# ---------------------------------------------------------------------------

class TestGetProductForecast:

    def test_returns_dict_for_known_product(self, clean_database):
        _seed_products(clean_database)
        svc = ForecastService(db_manager=clean_database)
        result = svc.get_product_forecast("SKU-1", days=30, horizon_days=7)
        assert isinstance(result, dict)
        assert result is not None

    def test_returns_none_for_unknown_product(self, clean_database):
        svc = ForecastService(db_manager=clean_database)
        result = svc.get_product_forecast("DOES_NOT_EXIST")
        assert result is None

    def test_expected_keys_present(self, clean_database):
        _seed_products(clean_database)
        svc = ForecastService(db_manager=clean_database)
        result = svc.get_product_forecast("SKU-1", days=30, horizon_days=7)
        required = {
            "product_id", "product_name", "method",
            "horizon_days", "forecast_daily", "forecast_total",
            "historical_daily_avg", "std_dev", "mae",
            "historical_dates", "historical_quantities",
            "forecast_dates", "forecast_values",
        }
        assert required.issubset(result.keys())

    def test_sma_forecast_close_to_actual(self, clean_database):
        _seed_products(clean_database)
        svc = ForecastService(db_manager=clean_database)
        # SKU-1 has constant 10 units/day → SMA should predict ~10
        result = svc.get_product_forecast(
            "SKU-1", days=30, horizon_days=7, method="SMA", window=14
        )
        assert result["forecast_daily"] == pytest.approx(10.0, abs=0.5)

    def test_forecast_dates_length_matches_horizon(self, clean_database):
        _seed_products(clean_database)
        svc = ForecastService(db_manager=clean_database)
        result = svc.get_product_forecast("SKU-1", days=30, horizon_days=14)
        assert len(result["forecast_dates"]) == 14
        assert len(result["forecast_values"]) == 14

    def test_historical_dates_length(self, clean_database):
        _seed_products(clean_database)
        svc = ForecastService(db_manager=clean_database)
        result = svc.get_product_forecast("SKU-1", days=30, horizon_days=7)
        # Should have 30 days of history (up to yesterday)
        assert len(result["historical_dates"]) == 30

    def test_wma_method(self, clean_database):
        _seed_products(clean_database)
        svc = ForecastService(db_manager=clean_database)
        result = svc.get_product_forecast("SKU-1", days=30, horizon_days=7, method="WMA")
        assert result["method"] == "WMA"
        assert result["forecast_daily"] > 0

    def test_linear_method(self, clean_database):
        _seed_products(clean_database)
        svc = ForecastService(db_manager=clean_database)
        result = svc.get_product_forecast("SKU-1", days=30, horizon_days=7, method="LINEAR")
        assert result["method"] == "LINEAR"
        assert result["forecast_daily"] >= 0


# ---------------------------------------------------------------------------
# get_reorder_recommendations
# ---------------------------------------------------------------------------

class TestGetReorderRecommendations:

    def test_returns_list(self, clean_database):
        _seed_products(clean_database)
        svc = ForecastService(db_manager=clean_database)
        result = svc.get_reorder_recommendations(days=30, lead_time_days=7)
        assert isinstance(result, list)

    def test_one_row_per_product(self, clean_database):
        _seed_products(clean_database)
        svc = ForecastService(db_manager=clean_database)
        result = svc.get_reorder_recommendations(days=30)
        ids = {r["product_id"] for r in result}
        assert ids == {"SKU-1", "SKU-2"}

    def test_expected_keys_present(self, clean_database):
        _seed_products(clean_database)
        svc = ForecastService(db_manager=clean_database)
        result = svc.get_reorder_recommendations(days=30)
        required = {
            "product_id", "product_name", "category",
            "current_stock", "avg_daily_demand", "forecast_daily",
            "safety_stock", "reorder_point", "days_until_stockout",
            "urgency", "lead_time_days",
        }
        for row in result:
            assert required.issubset(row.keys())

    def test_urgency_values_valid(self, clean_database):
        _seed_products(clean_database)
        svc = ForecastService(db_manager=clean_database)
        result = svc.get_reorder_recommendations(days=30)
        valid_urgencies = {"CRITICAL", "WARNING", "OK", "NO DEMAND"}
        for row in result:
            assert row["urgency"] in valid_urgencies

    def test_low_stock_is_critical(self, clean_database):
        _seed_products(clean_database)
        svc = ForecastService(db_manager=clean_database)
        # SKU-1: 50 units, 10/day → 5 days of supply, lead_time=7 → CRITICAL
        result = svc.get_reorder_recommendations(days=30, lead_time_days=7)
        sku1 = next(r for r in result if r["product_id"] == "SKU-1")
        assert sku1["urgency"] == "CRITICAL"

    def test_high_stock_is_ok(self, clean_database):
        _seed_products(clean_database)
        svc = ForecastService(db_manager=clean_database)
        # SKU-2: 200 units, 2/day → 100 days of supply → OK
        result = svc.get_reorder_recommendations(days=30, lead_time_days=7)
        sku2 = next(r for r in result if r["product_id"] == "SKU-2")
        assert sku2["urgency"] == "OK"

    def test_sorted_by_urgency(self, clean_database):
        _seed_products(clean_database)
        svc = ForecastService(db_manager=clean_database)
        result = svc.get_reorder_recommendations(days=30, lead_time_days=7)
        urgency_rank = {"CRITICAL": 0, "WARNING": 1, "OK": 2, "NO DEMAND": 3}
        ranks = [urgency_rank[r["urgency"]] for r in result]
        assert ranks == sorted(ranks)

    def test_reorder_point_positive(self, clean_database):
        _seed_products(clean_database)
        svc = ForecastService(db_manager=clean_database)
        result = svc.get_reorder_recommendations(days=30)
        for row in result:
            assert row["reorder_point"] >= 0

    def test_category_filter(self, clean_database):
        _seed_products(clean_database)
        svc = ForecastService(db_manager=clean_database)
        result = svc.get_reorder_recommendations(days=30, category="Cat1")
        ids = {r["product_id"] for r in result}
        assert ids == {"SKU-1"}

    def test_empty_database_returns_empty(self, clean_database):
        svc = ForecastService(db_manager=clean_database)
        result = svc.get_reorder_recommendations(days=30)
        assert result == []


# ---------------------------------------------------------------------------
# get_categories / get_products
# ---------------------------------------------------------------------------

class TestHelpers:

    def test_get_categories(self, clean_database):
        _seed_products(clean_database)
        svc = ForecastService(db_manager=clean_database)
        cats = svc.get_categories()
        assert set(cats) == {"Cat1", "Cat2"}

    def test_get_products(self, clean_database):
        _seed_products(clean_database)
        svc = ForecastService(db_manager=clean_database)
        products = svc.get_products()
        ids = {p["product_id"] for p in products}
        assert ids == {"SKU-1", "SKU-2"}

    def test_get_products_category_filter(self, clean_database):
        _seed_products(clean_database)
        svc = ForecastService(db_manager=clean_database)
        products = svc.get_products(category="Cat2")
        assert all(p["category"] == "Cat2" for p in products)
