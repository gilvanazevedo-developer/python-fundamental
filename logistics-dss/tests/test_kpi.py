"""
Tests for KPI Service
"""

import pytest
import sys
from pathlib import Path
from decimal import Decimal
from datetime import date, datetime, timedelta

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.database.models import Product, Warehouse, InventoryLevel, SalesRecord
from src.services.kpi_service import KPIService


@pytest.fixture
def kpi_db(clean_database):
    """Create a database with controlled data for KPI testing."""
    db = clean_database

    with db.get_session() as session:
        # 3 products, different categories
        session.add(Product(id="P1", name="Product 1", category="CatA",
                           unit_cost=Decimal("10.00"), unit_price=Decimal("20.00")))
        session.add(Product(id="P2", name="Product 2", category="CatA",
                           unit_cost=Decimal("20.00"), unit_price=Decimal("40.00")))
        session.add(Product(id="P3", name="Product 3", category="CatB",
                           unit_cost=Decimal("5.00"), unit_price=Decimal("15.00")))

        # 1 warehouse
        session.add(Warehouse(id="W1", name="Warehouse 1",
                             location="Location 1", capacity=10000))

    with db.get_session() as session:
        # Inventory: P1=100, P2=200, P3=0 (stockout)
        session.add(InventoryLevel(product_id="P1", warehouse_id="W1",
                                   quantity=100, last_updated=datetime.now()))
        session.add(InventoryLevel(product_id="P2", warehouse_id="W1",
                                   quantity=200, last_updated=datetime.now()))
        session.add(InventoryLevel(product_id="P3", warehouse_id="W1",
                                   quantity=0, last_updated=datetime.now()))

        # Sales: 10 units/day for P1, 5 units/day for P2, over 10 days
        today = date.today()
        for i in range(10):
            d = today - timedelta(days=i)
            session.add(SalesRecord(date=d, product_id="P1", warehouse_id="W1",
                                    quantity_sold=10, revenue=Decimal("200.00")))
            session.add(SalesRecord(date=d, product_id="P2", warehouse_id="W1",
                                    quantity_sold=5, revenue=Decimal("200.00")))

    return db


class TestKPIService:
    """Tests for KPIService."""

    def test_stock_health_kpis(self, kpi_db):
        service = KPIService(kpi_db)
        kpis = service.get_stock_health_kpis(days=30)

        assert kpis["total_products"] == 3
        assert kpis["total_units"] == 300  # 100 + 200 + 0
        assert kpis["avg_daily_demand"] > 0

    def test_days_of_supply(self, kpi_db):
        service = KPIService(kpi_db)
        kpis = service.get_stock_health_kpis(days=30)

        # Total units = 300, total sold in 30 days = 10*10 + 5*10 = 150
        # Avg daily demand = 150/30 = 5
        # Days of supply = 300/5 = 60
        assert kpis["days_of_supply"] == pytest.approx(60.0, rel=0.1)

    def test_service_level_kpis(self, kpi_db):
        service = KPIService(kpi_db)
        kpis = service.get_service_level_kpis()

        # P3 has 0 stock → 1 stockout out of 3 products
        assert kpis["stockout_count"] == 1
        assert kpis["stockout_rate"] == pytest.approx(33.3, abs=0.5)
        assert kpis["fill_rate"] == pytest.approx(66.7, abs=0.5)

    def test_financial_kpis(self, kpi_db):
        service = KPIService(kpi_db)
        kpis = service.get_financial_kpis(days=30)

        # Inventory value: 100*10 + 200*20 + 0*5 = 5000
        assert kpis["total_inventory_value"] == 5000.0
        # Retail value: 100*20 + 200*40 + 0*15 = 10000
        assert kpis["total_retail_value"] == 10000.0
        # Potential margin: 10000 - 5000 = 5000
        assert kpis["potential_margin"] == 5000.0
        # Carrying cost monthly: 5000 * 0.25 / 12 ≈ 104.17
        assert kpis["carrying_cost_monthly"] == pytest.approx(104.17, abs=1)

    def test_get_all_kpis(self, kpi_db):
        service = KPIService(kpi_db)
        kpis = service.get_all_kpis(days=30)

        assert "stock_health" in kpis
        assert "service_level" in kpis
        assert "financial" in kpis
        assert kpis["stock_health"]["total_products"] == 3

    def test_product_kpis(self, kpi_db):
        service = KPIService(kpi_db)
        kpis = service.get_product_kpis("P1", days=30)

        assert kpis["product_id"] == "P1"
        assert kpis["total_stock"] == 100
        assert kpis["warehouse_count"] == 1
        # 100 units sold over 30 days → avg demand ~3.33/day
        assert kpis["avg_daily_demand"] == pytest.approx(100.0 / 30, rel=0.1)
        # Days of supply = 100 / (100/30) = 30
        assert kpis["days_of_supply"] == pytest.approx(30.0, rel=0.5)

    def test_product_kpis_no_sales(self, kpi_db):
        service = KPIService(kpi_db)
        kpis = service.get_product_kpis("P3", days=30)

        assert kpis["total_stock"] == 0
        assert kpis["avg_daily_demand"] == 0.0
        assert kpis["days_of_supply"] is None  # No demand → undefined

    def test_kpis_with_category_filter(self, kpi_db):
        service = KPIService(kpi_db)
        kpis = service.get_stock_health_kpis(category="CatA", days=30)

        # Only P1 and P2 in CatA
        assert kpis["total_products"] == 2
        assert kpis["total_units"] == 300  # 100 + 200

    def test_kpis_empty_database(self, clean_database):
        service = KPIService(clean_database)
        kpis = service.get_all_kpis(days=30)

        assert kpis["stock_health"]["total_products"] == 0
        assert kpis["stock_health"]["total_units"] == 0
        assert kpis["financial"]["total_inventory_value"] == 0.0
        assert kpis["service_level"]["stockout_count"] == 0
