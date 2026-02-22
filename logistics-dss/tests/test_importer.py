"""
Tests for Data Importer Module
"""

import pytest
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

import pandas as pd

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from config.constants import DataType
from src.importer.base import ImportResult
from src.importer.csv_importer import CSVImporter
from src.importer.excel_importer import ExcelImporter


class TestImportResult:
    """Tests for ImportResult dataclass."""

    def test_success_summary(self):
        """Test summary for successful import."""
        result = ImportResult(
            success=True,
            data_type=DataType.PRODUCTS,
            filename="products.csv",
            total_records=100,
            imported_records=100,
            failed_records=0
        )
        assert "succeeded" in result.summary
        assert "100/100" in result.summary

    def test_failed_summary(self):
        """Test summary for failed import."""
        result = ImportResult(
            success=False,
            data_type=DataType.PRODUCTS,
            filename="products.csv",
            total_records=100,
            imported_records=0,
            failed_records=100
        )
        assert "failed" in result.summary

    def test_to_dict(self):
        """Test conversion to dictionary."""
        result = ImportResult(
            success=True,
            data_type=DataType.PRODUCTS,
            filename="test.csv",
            total_records=10,
            imported_records=10,
            failed_records=0,
            duration_seconds=1.5
        )
        d = result.to_dict()
        assert d["success"] is True
        assert d["data_type"] == "products"
        assert d["duration_seconds"] == 1.5


class TestCSVImporter:
    """Tests for CSVImporter class."""

    def test_read_valid_csv(self, sample_csv_file):
        """Test reading a valid CSV file."""
        importer = CSVImporter(DataType.PRODUCTS)
        df = importer.read_file(sample_csv_file)
        assert len(df) == 3
        assert "id" in df.columns

    def test_validate_columns_success(self, sample_products_df):
        """Test column validation with all required columns."""
        importer = CSVImporter(DataType.PRODUCTS)
        df = importer.normalize_columns(sample_products_df)
        is_valid = importer.validate_columns(df)
        assert is_valid is True

    def test_validate_columns_missing(self):
        """Test column validation with missing columns."""
        importer = CSVImporter(DataType.PRODUCTS)
        df = pd.DataFrame({"id": ["SKU001"], "name": ["Test"]})
        is_valid = importer.validate_columns(df)
        assert is_valid is False
        assert len(importer.errors) > 0
        assert importer.errors[0]["type"] == "missing_columns"

    def test_import_invalid_file(self, invalid_csv_file):
        """Test importing file with missing columns."""
        importer = CSVImporter(DataType.PRODUCTS)

        # Mock database manager to avoid actual DB operations
        with patch.object(importer, 'db_manager'):
            result = importer.import_file(invalid_csv_file)

        assert result.success is False
        assert any("missing_columns" in str(e) for e in result.errors)

    def test_import_nonexistent_file(self, temp_dir):
        """Test importing a file that doesn't exist."""
        importer = CSVImporter(DataType.PRODUCTS)
        fake_path = temp_dir / "nonexistent.csv"

        result = importer.import_file(fake_path)

        assert result.success is False
        assert any("not_found" in str(e.get("type", "")) for e in result.errors)

    def test_normalize_columns(self):
        """Test column normalization."""
        importer = CSVImporter(DataType.PRODUCTS)
        df = pd.DataFrame({
            "  ID  ": ["SKU001"],
            "Name": ["Test"],
            "CATEGORY": ["Cat"]
        })
        normalized = importer.normalize_columns(df)
        assert list(normalized.columns) == ["id", "name", "category"]

    def test_type_conversion_decimal(self):
        """Test decimal type conversion."""
        importer = CSVImporter(DataType.PRODUCTS)

        result = importer._to_decimal("19.99")
        from decimal import Decimal
        assert result == Decimal("19.99")

    def test_type_conversion_int(self):
        """Test integer type conversion."""
        importer = CSVImporter(DataType.PRODUCTS)

        result = importer._to_int("100")
        assert result == 100

        result = importer._to_int("100.0")
        assert result == 100

    def test_type_conversion_date(self):
        """Test date type conversion."""
        importer = CSVImporter(DataType.PRODUCTS)

        result = importer._to_date("2024-01-15")
        from datetime import date
        assert result == date(2024, 1, 15)


class TestExcelImporter:
    """Tests for ExcelImporter class."""

    def test_read_valid_excel(self, sample_excel_file):
        """Test reading a valid Excel file."""
        importer = ExcelImporter(DataType.PRODUCTS)
        df = importer.read_file(sample_excel_file)
        assert len(df) == 3

    def test_get_sheet_names(self, sample_excel_file):
        """Test getting sheet names."""
        importer = ExcelImporter(DataType.PRODUCTS)
        sheets = importer.get_sheet_names(sample_excel_file)
        assert len(sheets) >= 1

    def test_import_specific_sheet(self, sample_excel_file):
        """Test importing a specific sheet."""
        importer = ExcelImporter(DataType.PRODUCTS)
        sheets = importer.get_sheet_names(sample_excel_file)

        # Mock database to avoid actual DB operations
        with patch.object(importer, 'db_manager'):
            with patch.object(importer, '_save_to_database', return_value=3):
                with patch.object(importer, '_log_import'):
                    result = importer.import_sheet(sample_excel_file, sheets[0])

        assert result.total_records == 3


class TestImporterIntegration:
    """Integration tests for importers with database."""

    def test_full_import_workflow(self, sample_csv_file, clean_database):
        """Test complete import workflow."""
        importer = CSVImporter(DataType.PRODUCTS)
        # Use the clean database from fixture
        importer.db_manager = clean_database

        result = importer.import_file(sample_csv_file)

        assert result.success is True
        assert result.imported_records == 3
        assert result.failed_records == 0

        # Verify data in database
        from src.database.models import Product
        with clean_database.get_session() as session:
            products = session.query(Product).all()
            assert len(products) == 3

    def test_import_with_validation_errors(self, csv_with_invalid_data, clean_database):
        """Test import with some invalid rows."""
        importer = CSVImporter(DataType.PRODUCTS)

        result = importer.import_file(csv_with_invalid_data)

        # Some records should fail validation
        assert result.failed_records > 0
