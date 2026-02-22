"""
Unit tests for src/services/import_wizard_service.py (T8-30)
8 tests covering product validation, import, duplicate handling, demand validation,
and audit event emission.
"""

import sys
import json
from pathlib import Path
from datetime import datetime, timedelta

import pandas as pd
import pytest

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import src.services.auth_service as auth_module
from src.services.import_wizard_service import ImportWizardService, ImportValidationError
from src.repositories.audit_event_repository import AuditEventRepository
from src.database.models import Product, Warehouse


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_product_csv(tmp_path, rows: list[dict]) -> str:
    df = pd.DataFrame(rows)
    p = tmp_path / "products.csv"
    df.to_csv(p, index=False)
    return str(p)


def _make_demand_csv(tmp_path, rows: list[dict]) -> str:
    df = pd.DataFrame(rows)
    p = tmp_path / "demand.csv"
    df.to_csv(p, index=False)
    return str(p)


def _seed_product(db, sku: str, name: str = "Test"):
    """Insert a Product row directly into the test DB."""
    with db.get_session() as session:
        if not session.get(Product, sku):
            session.add(Product(
                id=sku, name=name, category="Cat",
                unit_cost=1.0, unit_price=2.0,
                created_at=datetime.utcnow(), updated_at=datetime.utcnow(),
            ))


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def clear_session():
    auth_module._current_user = None
    yield
    auth_module._current_user = None


@pytest.fixture
def svc(clean_database):
    return ImportWizardService()


@pytest.fixture
def valid_product_rows():
    return [
        {"sku": f"SKU{i:03d}", "name": f"Product {i}", "category": "Cat",
         "unit_cost": 10.0, "abc_class": "A"}
        for i in range(1, 6)
    ]


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestImportWizard:

    def test_validate_product_csv_valid(self, svc, tmp_path, valid_product_rows):
        """5-row valid CSV → {errors: [], warnings: [], row_count: 5}."""
        path = _make_product_csv(tmp_path, valid_product_rows)
        result = svc.validate_product_file(path)
        assert result["errors"] == []
        assert result["row_count"] == 5

    def test_validate_product_csv_missing_required_column(self, svc, tmp_path):
        """CSV without 'sku' column → errors contains 'Required column sku not found'."""
        rows = [{"name": "Product A", "category": "Cat", "unit_cost": 5.0}]
        path = _make_product_csv(tmp_path, rows)
        result = svc.validate_product_file(path)
        assert any("sku" in e.lower() for e in result["errors"])

    def test_validate_product_csv_invalid_unit_cost(self, svc, tmp_path):
        """Row with unit_cost=-5 → errors contains 'unit_cost must be ≥ 0'."""
        rows = [{"sku": "SKU001", "name": "Product A", "unit_cost": -5}]
        path = _make_product_csv(tmp_path, rows)
        result = svc.validate_product_file(path)
        assert any("unit_cost" in e for e in result["errors"])

    def test_import_products_inserts_rows(self, svc, tmp_path, valid_product_rows, clean_database):
        """5-row valid CSV → 5 Product rows in DB; imported_count=5, skipped_count=0."""
        path = _make_product_csv(tmp_path, valid_product_rows)
        result = svc.import_products(path)
        assert result["imported_count"] == 5
        assert result["skipped_count"] == 0

        db = clean_database
        with db.get_session() as session:
            count = session.query(Product).count()
        assert count == 5

    def test_import_products_skip_duplicates(self, svc, tmp_path, clean_database):
        """CSV with 2 new + 1 existing SKU (overwrite_existing=False) → imported=2, skipped=1."""
        _seed_product(clean_database, "SKU001")

        rows = [
            {"sku": "SKU001", "name": "Existing", "unit_cost": 1.0},
            {"sku": "SKU002", "name": "New Two",  "unit_cost": 2.0},
            {"sku": "SKU003", "name": "New Three", "unit_cost": 3.0},
        ]
        path = _make_product_csv(tmp_path, rows)
        result = svc.import_products(path, overwrite_existing=False)
        assert result["imported_count"] == 2
        assert result["skipped_count"] == 1

    def test_import_products_overwrite_duplicates(self, svc, tmp_path, clean_database):
        """CSV with 1 existing SKU (overwrite_existing=True) → product name updated; imported=1."""
        _seed_product(clean_database, "SKU001", name="Old Name")

        rows = [{"sku": "SKU001", "name": "Updated Name", "unit_cost": 5.0}]
        path = _make_product_csv(tmp_path, rows)
        result = svc.import_products(path, overwrite_existing=True)
        assert result["imported_count"] == 1
        assert result["skipped_count"] == 0

        with clean_database.get_session() as session:
            p = session.get(Product, "SKU001")
            assert p.name == "Updated Name"

    def test_import_demand_unknown_sku_raises(self, svc, tmp_path, clean_database):
        """Demand CSV referencing 'SKU999' (not in Product table) → ImportValidationError."""
        rows = [{"sku": "SKU999", "date": "2026-01-01", "quantity": 10}]
        path = _make_demand_csv(tmp_path, rows)
        with pytest.raises(ImportValidationError):
            svc.validate_demand_file(path)

    def test_import_logs_audit_event(self, svc, tmp_path, valid_product_rows, clean_database):
        """After import_products() → AuditEvent row with event_type='PRODUCTS' and correct detail."""
        path = _make_product_csv(tmp_path, valid_product_rows)
        result = svc.import_products(path)

        from config.constants import IMPORT_TYPE_PRODUCTS
        repo = AuditEventRepository()
        events = repo.get_by_event_type(IMPORT_TYPE_PRODUCTS)
        assert len(events) >= 1

        latest = events[0]
        detail = json.loads(latest.detail)
        assert detail["import_type"] == IMPORT_TYPE_PRODUCTS
        assert detail["imported"] == result["imported_count"]
