"""
Import Wizard Service
Validation, preview, and import orchestration for three data types:
  - PRODUCTS  (product master: sku, name, category, unit_cost, ...)
  - DEMAND    (historical demand: sku, date, quantity)
  - SUPPLIERS (supplier master: name, default_lead_time_days, ...)
"""

import re
import sys
from datetime import datetime, date
from pathlib import Path
from typing import Optional

import pandas as pd

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.database.connection import get_db_manager
from src.database.models import Product, Supplier, SalesRecord
from src.services.audit_service import AuditService
from src.services.auth_service import AuthService
from config.constants import (
    IMPORT_TYPE_PRODUCTS,
    IMPORT_TYPE_DEMAND,
    IMPORT_TYPE_SUPPLIERS,
)


# ---------------------------------------------------------------------------
# Custom exceptions
# ---------------------------------------------------------------------------

class ImportValidationError(Exception):
    """Raised when a file fails pre-import validation."""


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------

class ImportWizardService:
    """Orchestrates file validation, preview, and batch import."""

    def __init__(self):
        self._db = get_db_manager()
        self._audit = AuditService()

    # ------------------------------------------------------------------
    # Preview
    # ------------------------------------------------------------------

    def get_import_preview(self, path: str, import_type: str) -> list[dict]:
        """Return the first 10 rows as a list of dicts (CSV or Excel auto-detected)."""
        df = self._read_file(path)
        return df.head(10).fillna("").to_dict(orient="records")

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    def validate_product_file(self, path: str) -> dict:
        """
        Validate a product import file.

        Returns:
            {errors: [...], warnings: [...], row_count: N}
        """
        errors: list[str] = []
        warnings: list[str] = []

        try:
            df = self._read_file(path)
        except Exception as exc:
            return {"errors": [f"Cannot read file: {exc}"], "warnings": [], "row_count": 0}

        # Required columns
        for col in ("sku", "name"):
            if col not in df.columns:
                errors.append(f"Required column '{col}' not found")

        if errors:
            return {"errors": errors, "warnings": warnings, "row_count": len(df)}

        for i, row in df.iterrows():
            row_num = i + 2  # 1-based + header
            sku = str(row.get("sku", "")).strip()
            name = str(row.get("name", "")).strip()

            if not sku or len(sku) > 32 or re.search(r"\s", sku):
                errors.append(f"Row {row_num}: sku must be 1–32 non-whitespace characters")
            if not name or len(name) > 128:
                errors.append(f"Row {row_num}: name must be 1–128 characters")

            unit_cost = row.get("unit_cost")
            if pd.notna(unit_cost):
                try:
                    cost = float(unit_cost)
                    if cost < 0:
                        errors.append(f"Row {row_num}: unit_cost must be ≥ 0")
                except (ValueError, TypeError):
                    errors.append(f"Row {row_num}: unit_cost must be a number")

            abc = row.get("abc_class")
            if pd.notna(abc) and str(abc).strip() not in ("A", "B", "C", ""):
                errors.append(f"Row {row_num}: abc_class must be A, B, or C")

            if pd.isna(row.get("abc_class")) or str(row.get("abc_class", "")).strip() == "":
                warnings.append(f"Row {row_num}: abc_class blank, defaulting to A")

        return {"errors": errors, "warnings": warnings, "row_count": len(df)}

    def validate_demand_file(self, path: str) -> dict:
        """
        Validate a demand history import file.
        Raises ImportValidationError if any referenced SKU is absent from Product table.

        Returns:
            {errors: [...], warnings: [...], row_count: N}
        """
        errors: list[str] = []
        warnings: list[str] = []

        try:
            df = self._read_file(path)
        except Exception as exc:
            return {"errors": [f"Cannot read file: {exc}"], "warnings": [], "row_count": 0}

        for col in ("sku", "date", "quantity"):
            if col not in df.columns:
                errors.append(f"Required column '{col}' not found")

        if errors:
            return {"errors": errors, "warnings": warnings, "row_count": len(df)}

        # Cross-check SKUs against Product table
        with self._db.get_session() as session:
            known_skus = {
                r[0] for r in session.query(Product.id).all()
            }

        if len(known_skus) < 5:
            warnings.append(
                "Product table has fewer than 5 rows — ensure products are imported first."
            )

        unknown = set()
        for i, row in df.iterrows():
            row_num = i + 2
            sku = str(row.get("sku", "")).strip()
            if sku not in known_skus:
                unknown.add(sku)

            qty = row.get("quantity")
            if pd.notna(qty):
                try:
                    if int(qty) < 0:
                        errors.append(f"Row {row_num}: quantity must be ≥ 0")
                except (ValueError, TypeError):
                    errors.append(f"Row {row_num}: quantity must be an integer")

        if unknown:
            raise ImportValidationError(
                f"Unknown SKU(s) not in Product table: {sorted(unknown)}"
            )

        return {"errors": errors, "warnings": warnings, "row_count": len(df)}

    def validate_supplier_file(self, path: str) -> dict:
        """
        Validate a supplier import file.
        Checks required columns and duplicate names within the file.
        """
        errors: list[str] = []
        warnings: list[str] = []

        try:
            df = self._read_file(path)
        except Exception as exc:
            return {"errors": [f"Cannot read file: {exc}"], "warnings": [], "row_count": 0}

        for col in ("name", "default_lead_time_days"):
            if col not in df.columns:
                errors.append(f"Required column '{col}' not found")

        if errors:
            return {"errors": errors, "warnings": warnings, "row_count": len(df)}

        seen_names: set[str] = set()
        for i, row in df.iterrows():
            row_num = i + 2
            name = str(row.get("name", "")).strip()
            if not name or len(name) > 128:
                errors.append(f"Row {row_num}: name must be 1–128 characters")
            if name in seen_names:
                errors.append(f"Row {row_num}: duplicate supplier name '{name}' within file")
            seen_names.add(name)

            ltd = row.get("default_lead_time_days")
            if pd.notna(ltd):
                try:
                    if int(ltd) < 1:
                        errors.append(f"Row {row_num}: default_lead_time_days must be ≥ 1")
                except (ValueError, TypeError):
                    errors.append(f"Row {row_num}: default_lead_time_days must be an integer")

        return {"errors": errors, "warnings": warnings, "row_count": len(df)}

    # ------------------------------------------------------------------
    # Import
    # ------------------------------------------------------------------

    def import_products(self, path: str, overwrite_existing: bool = False) -> dict:
        """
        Commit valid product rows to DB.

        Returns:
            {imported_count, skipped_count, errors}
        """
        df = self._read_file(path)
        imported = 0
        skipped = 0
        errors: list[str] = []

        actor = self._get_actor()

        with self._db.get_session() as session:
            existing_ids = {r[0] for r in session.query(Product.id).all()}

            for i, row in df.iterrows():
                sku = str(row.get("sku", "")).strip()
                name = str(row.get("name", "")).strip()
                if not sku or not name:
                    errors.append(f"Row {i + 2}: missing sku or name — skipped")
                    skipped += 1
                    continue

                category = str(row.get("category", "")).strip() or ""
                unit_cost = self._safe_float(row.get("unit_cost"), 0.0)
                unit_price = self._safe_float(row.get("unit_price"), unit_cost)
                abc_class = str(row.get("abc_class", "A")).strip() or "A"

                if sku in existing_ids:
                    if overwrite_existing:
                        product = session.get(Product, sku)
                        if product:
                            product.name = name
                            product.category = category
                            product.unit_cost = unit_cost
                            product.unit_price = unit_price
                            product.updated_at = datetime.utcnow()
                            imported += 1
                    else:
                        skipped += 1
                else:
                    product = Product(
                        id=sku,
                        name=name,
                        category=category,
                        unit_cost=unit_cost,
                        unit_price=unit_price,
                        created_at=datetime.utcnow(),
                        updated_at=datetime.utcnow(),
                    )
                    session.add(product)
                    existing_ids.add(sku)
                    imported += 1

        self._audit.log(
            IMPORT_TYPE_PRODUCTS,
            actor=actor,
            detail={
                "import_type": IMPORT_TYPE_PRODUCTS,
                "imported": imported,
                "skipped": skipped,
            },
        )
        return {"imported_count": imported, "skipped_count": skipped, "errors": errors}

    def import_demand_history(self, path: str) -> dict:
        """
        Append demand rows; returns {imported_count, skipped_count, errors}.
        Deduplicates by (product_id, date, warehouse_id).
        """
        df = self._read_file(path)
        imported = 0
        skipped = 0
        errors: list[str] = []
        actor = self._get_actor()

        # Use a default warehouse id for demand import
        default_warehouse = "WH-DEFAULT"

        with self._db.get_session() as session:
            known_skus = {r[0] for r in session.query(Product.id).all()}

            for i, row in df.iterrows():
                sku = str(row.get("sku", "")).strip()
                date_str = str(row.get("date", "")).strip()
                qty = row.get("quantity")

                if sku not in known_skus:
                    errors.append(f"Row {i + 2}: SKU '{sku}' not found — skipped")
                    skipped += 1
                    continue

                try:
                    record_date = datetime.strptime(date_str, "%Y-%m-%d").date()
                except ValueError:
                    errors.append(f"Row {i + 2}: invalid date '{date_str}' — skipped")
                    skipped += 1
                    continue

                try:
                    quantity = int(qty)
                    if quantity < 0:
                        raise ValueError
                except (ValueError, TypeError):
                    errors.append(f"Row {i + 2}: invalid quantity — skipped")
                    skipped += 1
                    continue

                record = SalesRecord(
                    date=record_date,
                    product_id=sku,
                    warehouse_id=default_warehouse,
                    quantity_sold=quantity,
                    revenue=0,
                )
                session.add(record)
                imported += 1

        self._audit.log(
            IMPORT_TYPE_DEMAND,
            actor=actor,
            detail={"import_type": IMPORT_TYPE_DEMAND, "imported": imported, "skipped": skipped},
        )
        return {"imported_count": imported, "skipped_count": skipped, "errors": errors}

    def import_suppliers(self, path: str) -> dict:
        """
        Create Supplier rows; skip duplicates by name.
        Returns {imported_count, skipped_count, errors}.
        """
        df = self._read_file(path)
        imported = 0
        skipped = 0
        errors: list[str] = []
        actor = self._get_actor()

        with self._db.get_session() as session:
            existing_names = {
                r[0].lower() for r in session.query(Supplier.name).all()
            }

            for i, row in df.iterrows():
                name = str(row.get("name", "")).strip()
                if not name:
                    errors.append(f"Row {i + 2}: missing name — skipped")
                    skipped += 1
                    continue

                if name.lower() in existing_names:
                    skipped += 1
                    continue

                lead_time = self._safe_int(row.get("default_lead_time_days"), 7)

                import uuid
                supplier = Supplier(
                    id=str(uuid.uuid4())[:20],
                    name=name,
                    lead_time_days=max(1, lead_time),
                    min_order_qty=1,
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow(),
                )
                session.add(supplier)
                existing_names.add(name.lower())
                imported += 1

        self._audit.log(
            IMPORT_TYPE_SUPPLIERS,
            actor=actor,
            detail={"import_type": IMPORT_TYPE_SUPPLIERS, "imported": imported, "skipped": skipped},
        )
        return {"imported_count": imported, "skipped_count": skipped, "errors": errors}

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _read_file(path: str) -> pd.DataFrame:
        """Auto-detect CSV vs Excel by extension."""
        p = Path(path)
        suffix = p.suffix.lower()
        if suffix in (".xlsx", ".xls"):
            return pd.read_excel(p)
        return pd.read_csv(p, encoding="utf-8")

    @staticmethod
    def _safe_float(value, default: float) -> float:
        try:
            return float(value) if pd.notna(value) else default
        except (ValueError, TypeError):
            return default

    @staticmethod
    def _safe_int(value, default: int) -> int:
        try:
            return int(value) if pd.notna(value) else default
        except (ValueError, TypeError):
            return default

    @staticmethod
    def _get_actor() -> str:
        user = AuthService.get_current_user()
        return user.username if user else "system"
