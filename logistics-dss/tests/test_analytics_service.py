"""
Integration tests for src/services/analytics_service.py

Uses a clean in-memory SQLite database via the clean_database fixture.
"""

import sys
from pathlib import Path
from datetime import date, timedelta
from decimal import Decimal

import pytest

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.services.analytics_service import AnalyticsService
from src.database.models import Product, Warehouse, InventoryLevel, SalesRecord


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _seed_data(db_manager):
    """Populate the test database with a controlled dataset.

    Products:
        SKU-A  — 80 % of revenue  → class A
        SKU-B  — 12 % of revenue  → class B  (starts at 80 %, which is ≥70 % and <90 %)
        SKU-C  —  8 % of revenue  → class C  (starts at 92 %, which is ≥90 %)

    Revenue totals: SKU-A=800, SKU-B=120, SKU-C=80  (total=1000)
    Revenues chosen to keep class boundaries well clear of the 70 %/90 % thresholds.

    Warehouses: WH1
    Inventory: SKU-A=200, SKU-B=100, SKU-C=50
    """
    today = date.today()
    with db_manager.get_session() as session:
        # Products
        session.add(Product(id="SKU-A", name="Product A", category="Cat1",
                            unit_cost=Decimal("10"), unit_price=Decimal("20")))
        session.add(Product(id="SKU-B", name="Product B", category="Cat1",
                            unit_cost=Decimal("5"), unit_price=Decimal("10")))
        session.add(Product(id="SKU-C", name="Product C", category="Cat2",
                            unit_cost=Decimal("2"), unit_price=Decimal("4")))

        # Warehouse
        session.add(Warehouse(id="WH1", name="Main", location="Here", capacity=10000))

        # Inventory
        session.add(InventoryLevel(product_id="SKU-A", warehouse_id="WH1", quantity=200))
        session.add(InventoryLevel(product_id="SKU-B", warehouse_id="WH1", quantity=100))
        session.add(InventoryLevel(product_id="SKU-C", warehouse_id="WH1", quantity=50))

        # Sales recorded yesterday (within any 30-day window)
        for product_id, qty, rev in [
            ("SKU-A", 40, 800.0),
            ("SKU-B",  6, 120.0),
            ("SKU-C",  4,  80.0),
        ]:
            session.add(SalesRecord(
                date=today - timedelta(days=1),
                product_id=product_id,
                warehouse_id="WH1",
                quantity_sold=qty,
                revenue=Decimal(str(rev)),
            ))

        session.commit()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestGetAbcReport:

    def test_returns_list(self, clean_database):
        _seed_data(clean_database)
        svc = AnalyticsService(db_manager=clean_database)
        result = svc.get_abc_report(days=30)
        assert isinstance(result, list)

    def test_all_products_returned(self, clean_database):
        _seed_data(clean_database)
        svc = AnalyticsService(db_manager=clean_database)
        result = svc.get_abc_report(days=30)
        ids = {r["product_id"] for r in result}
        assert ids == {"SKU-A", "SKU-B", "SKU-C"}

    def test_sorted_by_revenue_descending(self, clean_database):
        _seed_data(clean_database)
        svc = AnalyticsService(db_manager=clean_database)
        result = svc.get_abc_report(days=30)
        revenues = [r["total_revenue"] for r in result]
        assert revenues == sorted(revenues, reverse=True)

    def test_abc_class_assigned(self, clean_database):
        _seed_data(clean_database)
        svc = AnalyticsService(db_manager=clean_database)
        result = svc.get_abc_report(days=30)
        classes = {r["product_id"]: r["abc_class"] for r in result}
        # SKU-A = 800/1000 = 80 % → A  (starts at 0 % < 70 %)
        assert classes["SKU-A"] == "A"
        # SKU-B = 120/1000 = 12 %, starts at 80 % (≥70 %, <90 %) → B
        assert classes["SKU-B"] == "B"
        # SKU-C = 80/1000 = 8 %, starts at 92 % (≥90 %) → C
        assert classes["SKU-C"] == "C"

    def test_current_stock_populated(self, clean_database):
        _seed_data(clean_database)
        svc = AnalyticsService(db_manager=clean_database)
        result = svc.get_abc_report(days=30)
        stock = {r["product_id"]: r["current_stock"] for r in result}
        assert stock["SKU-A"] == 200
        assert stock["SKU-B"] == 100
        assert stock["SKU-C"] == 50

    def test_turnover_rate_positive_when_stock_and_sales_exist(self, clean_database):
        _seed_data(clean_database)
        svc = AnalyticsService(db_manager=clean_database)
        result = svc.get_abc_report(days=30)
        for row in result:
            assert row["turnover_rate"] >= 0

    def test_days_of_inventory_populated(self, clean_database):
        _seed_data(clean_database)
        svc = AnalyticsService(db_manager=clean_database)
        result = svc.get_abc_report(days=30)
        # All seeded products have stock and sales
        for row in result:
            assert row["days_of_inventory"] is not None
            assert row["days_of_inventory"] > 0

    def test_expected_dict_keys(self, clean_database):
        _seed_data(clean_database)
        svc = AnalyticsService(db_manager=clean_database)
        result = svc.get_abc_report(days=30)
        required_keys = {
            "product_id", "product_name", "category",
            "total_revenue", "total_quantity",
            "revenue_pct", "cumulative_pct", "abc_class",
            "current_stock", "turnover_rate", "days_of_inventory",
        }
        for row in result:
            assert required_keys.issubset(row.keys())

    def test_empty_database_returns_empty(self, clean_database):
        svc = AnalyticsService(db_manager=clean_database)
        result = svc.get_abc_report(days=30)
        assert result == []

    def test_category_filter(self, clean_database):
        _seed_data(clean_database)
        svc = AnalyticsService(db_manager=clean_database)
        result = svc.get_abc_report(days=30, category="Cat2")
        ids = {r["product_id"] for r in result}
        assert ids == {"SKU-C"}


class TestGetAbcSummary:

    def test_always_returns_three_classes(self, clean_database):
        _seed_data(clean_database)
        svc = AnalyticsService(db_manager=clean_database)
        summaries = svc.get_abc_summary(days=30)
        assert len(summaries) == 3
        assert [s["abc_class"] for s in summaries] == ["A", "B", "C"]

    def test_product_counts(self, clean_database):
        _seed_data(clean_database)
        svc = AnalyticsService(db_manager=clean_database)
        summaries = {s["abc_class"]: s for s in svc.get_abc_summary(days=30)}
        # SKU-A → A, SKU-B → B, SKU-C → C  (one product per class)
        assert summaries["A"]["product_count"] == 1
        assert summaries["B"]["product_count"] == 1
        assert summaries["C"]["product_count"] == 1

    def test_revenue_pct_sums_near_100(self, clean_database):
        _seed_data(clean_database)
        svc = AnalyticsService(db_manager=clean_database)
        summaries = svc.get_abc_summary(days=30)
        total = sum(s["revenue_pct"] for s in summaries)
        assert abs(total - 100.0) < 1.0

    def test_empty_database_returns_zero_summaries(self, clean_database):
        svc = AnalyticsService(db_manager=clean_database)
        summaries = svc.get_abc_summary(days=30)
        assert len(summaries) == 3
        for s in summaries:
            assert s["product_count"] == 0

    def test_expected_dict_keys(self, clean_database):
        _seed_data(clean_database)
        svc = AnalyticsService(db_manager=clean_database)
        summaries = svc.get_abc_summary(days=30)
        required_keys = {
            "abc_class", "product_count", "total_revenue", "revenue_pct", "product_pct"
        }
        for s in summaries:
            assert required_keys.issubset(s.keys())


class TestGetCategories:

    def test_returns_list_of_strings(self, clean_database):
        _seed_data(clean_database)
        svc = AnalyticsService(db_manager=clean_database)
        cats = svc.get_categories()
        assert isinstance(cats, list)
        assert all(isinstance(c, str) for c in cats)

    def test_categories_sorted(self, clean_database):
        _seed_data(clean_database)
        svc = AnalyticsService(db_manager=clean_database)
        cats = svc.get_categories()
        assert cats == sorted(cats)

    def test_correct_categories_returned(self, clean_database):
        _seed_data(clean_database)
        svc = AnalyticsService(db_manager=clean_database)
        cats = svc.get_categories()
        assert set(cats) == {"Cat1", "Cat2"}

    def test_empty_database_returns_empty(self, clean_database):
        svc = AnalyticsService(db_manager=clean_database)
        cats = svc.get_categories()
        assert cats == []
