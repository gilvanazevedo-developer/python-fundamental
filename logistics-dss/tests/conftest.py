"""
Pytest Configuration and Shared Fixtures for Logistics DSS
"""

import os
import sys
import tempfile
import shutil
from pathlib import Path
from unittest.mock import MagicMock, patch
from datetime import datetime, date
from decimal import Decimal

import pytest
import pandas as pd

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


# ============================================================================
# Environment Setup
# ============================================================================

@pytest.fixture(scope="session", autouse=True)
def setup_test_environment():
    """Set up test environment variables."""
    os.environ.setdefault("LOG_LEVEL", "DEBUG")
    os.environ.setdefault("STRICT_VALIDATION", "true")
    yield


# ============================================================================
# Temporary Directories
# ============================================================================

@pytest.fixture
def temp_dir():
    """Create a temporary directory for test files."""
    temp_path = tempfile.mkdtemp()
    yield Path(temp_path)
    shutil.rmtree(temp_path, ignore_errors=True)


@pytest.fixture
def temp_database(temp_dir):
    """Create a temporary database path."""
    db_path = temp_dir / "test_logistics.db"
    return db_path


# ============================================================================
# Sample Data Fixtures
# ============================================================================

@pytest.fixture
def sample_products_df():
    """Sample products DataFrame."""
    return pd.DataFrame({
        "id": ["SKU001", "SKU002", "SKU003"],
        "name": ["Widget A", "Widget B", "Gadget C"],
        "category": ["Widgets", "Widgets", "Gadgets"],
        "unit_cost": ["10.50", "15.00", "25.00"],
        "unit_price": ["19.99", "29.99", "49.99"]
    })


@pytest.fixture
def sample_inventory_df():
    """Sample inventory DataFrame."""
    return pd.DataFrame({
        "product_id": ["SKU001", "SKU001", "SKU002"],
        "warehouse_id": ["WH001", "WH002", "WH001"],
        "quantity": ["100", "50", "200"],
        "last_updated": [
            "2024-01-15T10:00:00",
            "2024-01-15T10:00:00",
            "2024-01-15T11:00:00"
        ]
    })


@pytest.fixture
def sample_sales_df():
    """Sample sales DataFrame."""
    return pd.DataFrame({
        "date": ["2024-01-01", "2024-01-02", "2024-01-03"],
        "product_id": ["SKU001", "SKU001", "SKU002"],
        "warehouse_id": ["WH001", "WH001", "WH001"],
        "quantity_sold": ["10", "15", "20"],
        "revenue": ["199.90", "299.85", "599.80"]
    })


@pytest.fixture
def sample_warehouses_df():
    """Sample warehouses DataFrame."""
    return pd.DataFrame({
        "id": ["WH001", "WH002"],
        "name": ["Main Warehouse", "East Distribution"],
        "location": ["123 Main St, City", "456 East Ave, Town"],
        "capacity": ["10000", "5000"]
    })


@pytest.fixture
def sample_suppliers_df():
    """Sample suppliers DataFrame."""
    return pd.DataFrame({
        "id": ["SUP001", "SUP002"],
        "name": ["Acme Corp", "Global Supplies"],
        "lead_time_days": ["7", "14"],
        "min_order_qty": ["100", "50"]
    })


# ============================================================================
# CSV/Excel File Fixtures
# ============================================================================

@pytest.fixture
def sample_csv_file(temp_dir, sample_products_df):
    """Create a sample CSV file."""
    csv_path = temp_dir / "products.csv"
    sample_products_df.to_csv(csv_path, index=False)
    return csv_path


@pytest.fixture
def sample_excel_file(temp_dir, sample_products_df):
    """Create a sample Excel file."""
    excel_path = temp_dir / "products.xlsx"
    sample_products_df.to_excel(excel_path, index=False, engine="openpyxl")
    return excel_path


@pytest.fixture
def invalid_csv_file(temp_dir):
    """Create a CSV with missing required columns."""
    csv_path = temp_dir / "invalid.csv"
    df = pd.DataFrame({
        "id": ["SKU001"],
        "name": ["Widget"]
        # Missing: category, unit_cost, unit_price
    })
    df.to_csv(csv_path, index=False)
    return csv_path


@pytest.fixture
def csv_with_invalid_data(temp_dir):
    """Create a CSV with invalid data values."""
    csv_path = temp_dir / "invalid_data.csv"
    df = pd.DataFrame({
        "id": ["SKU001", "SKU002"],
        "name": ["Widget A", "Widget B"],
        "category": ["Widgets", "Widgets"],
        "unit_cost": ["-10.00", "invalid"],  # Invalid values
        "unit_price": ["19.99", "29.99"]
    })
    df.to_csv(csv_path, index=False)
    return csv_path


# ============================================================================
# Validation Fixtures
# ============================================================================

@pytest.fixture
def valid_product_row():
    """Valid product row for validation testing."""
    return {
        "id": "SKU001",
        "name": "Test Product",
        "category": "Test Category",
        "unit_cost": "10.00",
        "unit_price": "19.99"
    }


@pytest.fixture
def invalid_product_row():
    """Invalid product row for validation testing."""
    return {
        "id": "",  # Empty required field
        "name": "Test Product",
        "category": "Test Category",
        "unit_cost": "-10.00",  # Negative cost
        "unit_price": "invalid"  # Not a number
    }


# ============================================================================
# Database Fixtures
# ============================================================================

@pytest.fixture
def mock_db_session():
    """Create a mock database session."""
    session = MagicMock()
    session.commit = MagicMock()
    session.rollback = MagicMock()
    session.close = MagicMock()
    session.merge = MagicMock()
    session.add = MagicMock()
    return session


@pytest.fixture
def clean_database(temp_dir):
    """Set up clean test database with unique path per test."""
    import uuid
    unique_db = temp_dir / f"test_{uuid.uuid4().hex[:8]}.db"

    # Import and reset before patching
    from src.database.connection import DatabaseManager

    # Reset singleton completely
    if DatabaseManager._engine:
        DatabaseManager._engine.dispose()
    DatabaseManager._instance = None
    DatabaseManager._engine = None
    DatabaseManager._session_factory = None

    # Patch the settings module (connection.py now reads this dynamically)
    import config.settings
    original_path = config.settings.DATABASE_PATH
    config.settings.DATABASE_PATH = unique_db

    try:
        db_manager = DatabaseManager()
        db_manager.create_tables()

        yield db_manager

    finally:
        # Cleanup
        if DatabaseManager._engine:
            DatabaseManager._engine.dispose()
        DatabaseManager._instance = None
        DatabaseManager._engine = None
        DatabaseManager._session_factory = None
        config.settings.DATABASE_PATH = original_path


# ============================================================================
# Assertion Helpers
# ============================================================================

def assert_valid_import_result(result, expected_success=True):
    """Assert import result has expected structure."""
    assert hasattr(result, "success")
    assert hasattr(result, "total_records")
    assert hasattr(result, "imported_records")
    assert hasattr(result, "failed_records")
    assert hasattr(result, "errors")

    if expected_success:
        assert result.success is True
        assert result.failed_records == 0
    else:
        assert result.success is False or result.failed_records > 0


def assert_valid_validation_error(error):
    """Assert validation error has expected structure."""
    assert "field" in error
    assert "message" in error
