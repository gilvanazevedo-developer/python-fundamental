"""
Tests for Service Layer
"""

import pytest
import sys
from pathlib import Path
from decimal import Decimal
from datetime import date, datetime, timedelta

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.database.models import Product, Warehouse, Supplier, InventoryLevel, SalesRecord
from src.services.inventory_service import InventoryService
from src.services.sales_service import SalesService


@pytest.fixture
def populated_db(clean_database):
    """Create a database populated with sample data."""
    db = clean_database

    with db.get_session() as session:
        # Products
        session.add(Product(id="SKU001", name="Widget A", category="Widgets",
                           unit_cost=Decimal("10.00"), unit_price=Decimal("20.00")))
        session.add(Product(id="SKU002", name="Widget B", category="Widgets",
                           unit_cost=Decimal("15.00"), unit_price=Decimal("30.00")))
        session.add(Product(id="SKU003", name="Gadget C", category="Gadgets",
                           unit_cost=Decimal("25.00"), unit_price=Decimal("50.00")))
        session.add(Product(id="SKU004", name="Tool D", category="Tools",
                           unit_cost=Decimal("5.00"), unit_price=Decimal("12.00")))

        # Warehouses
        session.add(Warehouse(id="WH001", name="Main Warehouse",
                             location="123 Main St", capacity=10000))
        session.add(Warehouse(id="WH002", name="East Distribution",
                             location="456 East Ave", capacity=5000))

    with db.get_session() as session:
        # Inventory
        session.add(InventoryLevel(product_id="SKU001", warehouse_id="WH001",
                                   quantity=100, last_updated=datetime.now()))
        session.add(InventoryLevel(product_id="SKU001", warehouse_id="WH002",
                                   quantity=50, last_updated=datetime.now()))
        session.add(InventoryLevel(product_id="SKU002", warehouse_id="WH001",
                                   quantity=200, last_updated=datetime.now()))
        session.add(InventoryLevel(product_id="SKU003", warehouse_id="WH001",
                                   quantity=0, last_updated=datetime.now()))
        # SKU004 has no inventory records (zero stock)

        # Sales records (recent)
        today = date.today()
        for i in range(7):
            sale_date = today - timedelta(days=i)
            session.add(SalesRecord(date=sale_date, product_id="SKU001",
                                    warehouse_id="WH001", quantity_sold=10,
                                    revenue=Decimal("200.00")))
            session.add(SalesRecord(date=sale_date, product_id="SKU002",
                                    warehouse_id="WH001", quantity_sold=5,
                                    revenue=Decimal("150.00")))

    return db


class TestInventoryService:
    """Tests for InventoryService."""

    def test_get_all_products(self, populated_db):
        service = InventoryService(populated_db)
        products = service.get_all_products()
        assert len(products) == 4
        # Check Widget A has correct total stock (100 + 50)
        widget_a = next(p for p in products if p["id"] == "SKU001")
        assert widget_a["total_stock"] == 150

    def test_get_all_products_filter_category(self, populated_db):
        service = InventoryService(populated_db)
        products = service.get_all_products(category="Widgets")
        assert len(products) == 2
        assert all(p["category"] == "Widgets" for p in products)

    def test_get_all_products_filter_warehouse(self, populated_db):
        service = InventoryService(populated_db)
        products = service.get_all_products(warehouse_id="WH002")
        # Only SKU001 is in WH002
        assert len(products) == 1
        assert products[0]["id"] == "SKU001"
        assert products[0]["total_stock"] == 50

    def test_get_all_products_search(self, populated_db):
        service = InventoryService(populated_db)
        products = service.get_all_products(search="Gadget")
        assert len(products) == 1
        assert products[0]["id"] == "SKU003"

    def test_get_stock_by_product(self, populated_db):
        service = InventoryService(populated_db)
        stock = service.get_stock_by_product("SKU001")
        assert len(stock) == 2
        wh_ids = {s["warehouse_id"] for s in stock}
        assert wh_ids == {"WH001", "WH002"}

    def test_get_stock_summary(self, populated_db):
        service = InventoryService(populated_db)
        summary = service.get_stock_summary()
        assert summary["total_products"] == 4
        assert summary["total_units"] == 350  # 100 + 50 + 200 + 0
        assert summary["total_value"] == 100*10 + 50*10 + 200*15 + 0*25  # 4500
        assert summary["stockout_count"] >= 1  # SKU003 has 0, SKU004 has no inventory

    def test_get_stock_by_category(self, populated_db):
        service = InventoryService(populated_db)
        data = service.get_stock_by_category()
        assert len(data) >= 1
        # Widgets should be present
        categories = [d["category"] for d in data]
        assert "Widgets" in categories

    def test_get_low_stock_items(self, populated_db):
        service = InventoryService(populated_db)
        low = service.get_low_stock_items(threshold=10)
        # SKU003 (0 stock) and SKU004 (no inventory) should be low
        ids = {item["id"] for item in low}
        assert "SKU003" in ids
        assert "SKU004" in ids

    def test_get_categories(self, populated_db):
        service = InventoryService(populated_db)
        cats = service.get_categories()
        assert "Widgets" in cats
        assert "Gadgets" in cats
        assert "Tools" in cats

    def test_get_warehouses(self, populated_db):
        service = InventoryService(populated_db)
        warehouses = service.get_warehouses()
        assert len(warehouses) == 2
        names = {w["name"] for w in warehouses}
        assert "Main Warehouse" in names

    def test_search_products(self, populated_db):
        service = InventoryService(populated_db)
        results = service.search_products("Widget")
        assert len(results) == 2


class TestSalesService:
    """Tests for SalesService."""

    def test_get_sales_by_period(self, populated_db):
        service = SalesService(populated_db)
        today = date.today()
        start = today - timedelta(days=7)
        sales = service.get_sales_by_period(start, today)
        assert len(sales) == 14  # 7 days * 2 products

    def test_get_daily_sales_summary(self, populated_db):
        service = SalesService(populated_db)
        summary = service.get_daily_sales_summary(days=30)
        assert len(summary) == 7  # 7 days with sales
        # Each day has 10 + 5 = 15 units and 200 + 150 = 350 revenue
        for day in summary:
            assert day["total_quantity"] == 15
            assert day["total_revenue"] == 350.0

    def test_get_sales_by_category(self, populated_db):
        service = SalesService(populated_db)
        data = service.get_sales_by_category(days=30)
        assert len(data) == 1  # Only Widgets have sales
        assert data[0]["category"] == "Widgets"
        assert data[0]["total_revenue"] == 7 * 350.0  # 2450

    def test_get_top_products(self, populated_db):
        service = SalesService(populated_db)
        top = service.get_top_products(n=5, days=30)
        assert len(top) == 2  # SKU001 and SKU002
        # SKU001 should be first (higher revenue: 7*200 = 1400 vs 7*150 = 1050)
        assert top[0]["id"] == "SKU001"

    def test_get_total_revenue(self, populated_db):
        service = SalesService(populated_db)
        revenue = service.get_total_revenue(days=30)
        assert revenue == 7 * 350.0  # 2450

    def test_get_total_quantity_sold(self, populated_db):
        service = SalesService(populated_db)
        qty = service.get_total_quantity_sold(days=30)
        assert qty == 7 * 15  # 105

    def test_get_average_daily_demand(self, populated_db):
        service = SalesService(populated_db)
        demand = service.get_average_daily_demand("SKU001", days=30)
        # 70 units sold over 30 days = ~2.33
        assert demand == pytest.approx(70.0 / 30, rel=0.01)

    def test_get_sales_day_count(self, populated_db):
        service = SalesService(populated_db)
        count = service.get_sales_day_count(days=30)
        assert count == 7

    def test_empty_sales(self, clean_database):
        service = SalesService(clean_database)
        summary = service.get_daily_sales_summary(days=30)
        assert len(summary) == 0
        revenue = service.get_total_revenue(days=30)
        assert revenue == 0.0
