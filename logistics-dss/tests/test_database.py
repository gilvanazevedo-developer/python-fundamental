"""
Tests for Database Module
"""

import pytest
import sys
from pathlib import Path
from decimal import Decimal
from datetime import datetime, date

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.database.models import (
    Base, Product, Warehouse, Supplier, InventoryLevel, SalesRecord, ImportLog
)


class TestProductModel:
    """Tests for Product model."""

    def test_create_product(self, clean_database):
        """Test creating a product."""
        with clean_database.get_session() as session:
            product = Product(
                id="SKU001",
                name="Test Product",
                category="Test Category",
                unit_cost=Decimal("10.00"),
                unit_price=Decimal("19.99")
            )
            session.add(product)

        # Verify it was saved
        with clean_database.get_session() as session:
            saved = session.query(Product).filter_by(id="SKU001").first()
            assert saved is not None
            assert saved.name == "Test Product"
            assert saved.unit_cost == Decimal("10.00")

    def test_product_repr(self):
        """Test Product string representation."""
        product = Product(id="SKU001", name="Widget")
        assert "SKU001" in repr(product)
        assert "Widget" in repr(product)


class TestWarehouseModel:
    """Tests for Warehouse model."""

    def test_create_warehouse(self, clean_database):
        """Test creating a warehouse."""
        with clean_database.get_session() as session:
            warehouse = Warehouse(
                id="WH001",
                name="Main Warehouse",
                location="123 Main St",
                capacity=10000
            )
            session.add(warehouse)

        with clean_database.get_session() as session:
            saved = session.query(Warehouse).filter_by(id="WH001").first()
            assert saved is not None
            assert saved.capacity == 10000


class TestSupplierModel:
    """Tests for Supplier model."""

    def test_create_supplier(self, clean_database):
        """Test creating a supplier."""
        with clean_database.get_session() as session:
            supplier = Supplier(
                id="SUP001",
                name="Acme Corp",
                lead_time_days=7,
                min_order_qty=100
            )
            session.add(supplier)

        with clean_database.get_session() as session:
            saved = session.query(Supplier).filter_by(id="SUP001").first()
            assert saved is not None
            assert saved.lead_time_days == 7


class TestInventoryLevelModel:
    """Tests for InventoryLevel model."""

    def test_create_inventory_level(self, clean_database):
        """Test creating an inventory level with relationships."""
        with clean_database.get_session() as session:
            # Create related entities with unique IDs
            product = Product(
                id="SKU_INV_001",
                name="Widget",
                category="Widgets",
                unit_cost=Decimal("10.00"),
                unit_price=Decimal("19.99")
            )
            warehouse = Warehouse(
                id="WH_INV_001",
                name="Main",
                location="123 Main St",
                capacity=10000
            )
            session.add(product)
            session.add(warehouse)

        with clean_database.get_session() as session:
            inventory = InventoryLevel(
                product_id="SKU_INV_001",
                warehouse_id="WH_INV_001",
                quantity=100,
                last_updated=datetime.now()
            )
            session.add(inventory)

        with clean_database.get_session() as session:
            saved = session.query(InventoryLevel).first()
            assert saved is not None
            assert saved.quantity == 100


class TestSalesRecordModel:
    """Tests for SalesRecord model."""

    def test_create_sales_record(self, clean_database):
        """Test creating a sales record."""
        with clean_database.get_session() as session:
            # Create related entities with unique IDs
            product = Product(
                id="SKU_SALE_001",
                name="Widget",
                category="Widgets",
                unit_cost=Decimal("10.00"),
                unit_price=Decimal("19.99")
            )
            warehouse = Warehouse(
                id="WH_SALE_001",
                name="Main",
                location="123 Main St",
                capacity=10000
            )
            session.add(product)
            session.add(warehouse)

        with clean_database.get_session() as session:
            sale = SalesRecord(
                date=date(2024, 1, 15),
                product_id="SKU_SALE_001",
                warehouse_id="WH_SALE_001",
                quantity_sold=10,
                revenue=Decimal("199.90")
            )
            session.add(sale)

        with clean_database.get_session() as session:
            saved = session.query(SalesRecord).first()
            assert saved is not None
            assert saved.quantity_sold == 10
            assert saved.revenue == Decimal("199.90")


class TestImportLogModel:
    """Tests for ImportLog model."""

    def test_create_import_log(self, clean_database):
        """Test creating an import log entry."""
        with clean_database.get_session() as session:
            log = ImportLog(
                filename="products.csv",
                data_type="products",
                records_total=100,
                records_imported=95,
                records_failed=5,
                status="partial",
                error_details="Sample errors"
            )
            session.add(log)

        with clean_database.get_session() as session:
            saved = session.query(ImportLog).first()
            assert saved is not None
            assert saved.records_imported == 95
            assert saved.status == "partial"


class TestDatabaseManager:
    """Tests for DatabaseManager class."""

    def test_singleton_pattern(self, clean_database):
        """Test that DatabaseManager is a singleton."""
        from src.database.connection import get_db_manager

        manager1 = get_db_manager()
        manager2 = get_db_manager()

        assert manager1 is manager2

    def test_session_context_manager(self, clean_database):
        """Test session context manager commits on success."""
        with clean_database.get_session() as session:
            product = Product(
                id="SKU999",
                name="Context Test",
                category="Test",
                unit_cost=Decimal("1.00"),
                unit_price=Decimal("2.00")
            )
            session.add(product)

        # Verify commit happened
        with clean_database.get_session() as session:
            found = session.query(Product).filter_by(id="SKU999").first()
            assert found is not None

    def test_session_rollback_on_error(self, clean_database):
        """Test session rollback on exception."""
        try:
            with clean_database.get_session() as session:
                product = Product(
                    id="SKU888",
                    name="Rollback Test",
                    category="Test",
                    unit_cost=Decimal("1.00"),
                    unit_price=Decimal("2.00")
                )
                session.add(product)
                raise ValueError("Simulated error")
        except ValueError:
            pass

        # Verify rollback happened
        with clean_database.get_session() as session:
            found = session.query(Product).filter_by(id="SKU888").first()
            assert found is None
