"""
Integration tests for src/services/optimization_service.py

Uses a clean in-memory SQLite database via the clean_database fixture.
"""

import sys
from pathlib import Path
from datetime import date, timedelta
from decimal import Decimal

import pytest

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.services.optimization_service import OptimizationService
from src.database.models import Product, Warehouse, InventoryLevel, SalesRecord


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _seed(db_manager):
    """Seed two products with different demand patterns and stock levels.

    SKU-X: 20 units/day, unit_cost=$10, stock=400  (well-stocked)
    SKU-Y:  5 units/day, unit_cost=$50, stock=50   (matches ~10 days supply)
    """
    today = date.today()
    with db_manager.get_session() as session:
        session.add(Product(id="SKU-X", name="Product X", category="CatA",
                            unit_cost=Decimal("10"), unit_price=Decimal("20")))
        session.add(Product(id="SKU-Y", name="Product Y", category="CatB",
                            unit_cost=Decimal("50"), unit_price=Decimal("80")))
        session.add(Warehouse(id="WH1", name="Main", location="City", capacity=10000))

        session.add(InventoryLevel(product_id="SKU-X", warehouse_id="WH1", quantity=400))
        session.add(InventoryLevel(product_id="SKU-Y", warehouse_id="WH1", quantity=50))

        for offset in range(1, 31):
            session.add(SalesRecord(
                date=today - timedelta(days=offset),
                product_id="SKU-X", warehouse_id="WH1",
                quantity_sold=20, revenue=Decimal("400"),
            ))
            session.add(SalesRecord(
                date=today - timedelta(days=offset),
                product_id="SKU-Y", warehouse_id="WH1",
                quantity_sold=5, revenue=Decimal("250"),
            ))
        session.commit()


# ---------------------------------------------------------------------------
# get_optimization_report
# ---------------------------------------------------------------------------

class TestGetOptimizationReport:

    def test_returns_list(self, clean_database):
        _seed(clean_database)
        svc = OptimizationService(db_manager=clean_database)
        result = svc.get_optimization_report(days=30)
        assert isinstance(result, list)

    def test_both_products_included(self, clean_database):
        _seed(clean_database)
        svc = OptimizationService(db_manager=clean_database)
        result = svc.get_optimization_report(days=30)
        ids = {r["product_id"] for r in result}
        assert ids == {"SKU-X", "SKU-Y"}

    def test_expected_keys(self, clean_database):
        _seed(clean_database)
        svc = OptimizationService(db_manager=clean_database)
        result = svc.get_optimization_report(days=30)
        required = {
            "product_id", "product_name", "category",
            "annual_demand", "eoq", "safety_stock", "reorder_point",
            "orders_per_year", "eoq_total_cost",
            "current_order_qty", "current_total_cost",
            "potential_savings", "savings_pct",
            "current_stock", "recommendation",
        }
        for row in result:
            assert required.issubset(row.keys())

    def test_sorted_by_savings_descending(self, clean_database):
        _seed(clean_database)
        svc = OptimizationService(db_manager=clean_database)
        result = svc.get_optimization_report(days=30)
        savings = [r["potential_savings"] for r in result]
        assert savings == sorted(savings, reverse=True)

    def test_eoq_positive(self, clean_database):
        _seed(clean_database)
        svc = OptimizationService(db_manager=clean_database)
        result = svc.get_optimization_report(days=30)
        for row in result:
            assert row["eoq"] > 0

    def test_potential_savings_non_negative(self, clean_database):
        _seed(clean_database)
        svc = OptimizationService(db_manager=clean_database)
        result = svc.get_optimization_report(days=30)
        for row in result:
            assert row["potential_savings"] >= 0

    def test_category_filter(self, clean_database):
        _seed(clean_database)
        svc = OptimizationService(db_manager=clean_database)
        result = svc.get_optimization_report(days=30, category="CatA")
        ids = {r["product_id"] for r in result}
        assert ids == {"SKU-X"}

    def test_custom_ordering_cost(self, clean_database):
        _seed(clean_database)
        svc = OptimizationService(db_manager=clean_database)
        low_cost = svc.get_optimization_report(days=30, ordering_cost=10)
        high_cost = svc.get_optimization_report(days=30, ordering_cost=200)
        # Higher ordering cost → higher EOQ → different costs
        low_eoq = {r["product_id"]: r["eoq"] for r in low_cost}
        high_eoq = {r["product_id"]: r["eoq"] for r in high_cost}
        for pid in low_eoq:
            assert high_eoq[pid] > low_eoq[pid]

    def test_empty_database_returns_empty(self, clean_database):
        svc = OptimizationService(db_manager=clean_database)
        result = svc.get_optimization_report(days=30)
        assert result == []

    def test_recommendation_field_is_string(self, clean_database):
        _seed(clean_database)
        svc = OptimizationService(db_manager=clean_database)
        result = svc.get_optimization_report(days=30)
        for row in result:
            assert isinstance(row["recommendation"], str)
            assert len(row["recommendation"]) > 0


# ---------------------------------------------------------------------------
# get_optimization_summary
# ---------------------------------------------------------------------------

class TestGetOptimizationSummary:

    def test_returns_dict(self, clean_database):
        _seed(clean_database)
        svc = OptimizationService(db_manager=clean_database)
        result = svc.get_optimization_summary(days=30)
        assert isinstance(result, dict)

    def test_expected_keys(self, clean_database):
        _seed(clean_database)
        svc = OptimizationService(db_manager=clean_database)
        result = svc.get_optimization_summary(days=30)
        required = {
            "total_current_cost", "total_optimal_cost", "total_savings",
            "savings_pct", "products_with_savings", "total_products",
        }
        assert required.issubset(result.keys())

    def test_total_savings_non_negative(self, clean_database):
        _seed(clean_database)
        svc = OptimizationService(db_manager=clean_database)
        result = svc.get_optimization_summary(days=30)
        assert result["total_savings"] >= 0

    def test_savings_pct_between_0_and_100(self, clean_database):
        _seed(clean_database)
        svc = OptimizationService(db_manager=clean_database)
        result = svc.get_optimization_summary(days=30)
        assert 0 <= result["savings_pct"] <= 100

    def test_total_products_matches_report(self, clean_database):
        _seed(clean_database)
        svc = OptimizationService(db_manager=clean_database)
        summary = svc.get_optimization_summary(days=30)
        report = svc.get_optimization_report(days=30)
        assert summary["total_products"] == len(report)

    def test_empty_database_returns_zeros(self, clean_database):
        svc = OptimizationService(db_manager=clean_database)
        result = svc.get_optimization_summary(days=30)
        assert result["total_products"] == 0
        assert result["total_savings"] == 0.0


# ---------------------------------------------------------------------------
# get_savings_by_category
# ---------------------------------------------------------------------------

class TestGetSavingsByCategory:

    def test_returns_list(self, clean_database):
        _seed(clean_database)
        svc = OptimizationService(db_manager=clean_database)
        result = svc.get_savings_by_category(days=30)
        assert isinstance(result, list)

    def test_categories_present(self, clean_database):
        _seed(clean_database)
        svc = OptimizationService(db_manager=clean_database)
        result = svc.get_savings_by_category(days=30)
        cats = {r["category"] for r in result}
        assert cats == {"CatA", "CatB"}

    def test_sorted_by_savings_descending(self, clean_database):
        _seed(clean_database)
        svc = OptimizationService(db_manager=clean_database)
        result = svc.get_savings_by_category(days=30)
        savings = [r["potential_savings"] for r in result]
        assert savings == sorted(savings, reverse=True)

    def test_expected_keys(self, clean_database):
        _seed(clean_database)
        svc = OptimizationService(db_manager=clean_database)
        result = svc.get_savings_by_category(days=30)
        for row in result:
            assert {"category", "potential_savings", "current_cost", "product_count"}.issubset(row.keys())
