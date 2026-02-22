"""
CSV File Importer
Handles importing data from CSV files.
"""

from pathlib import Path
from typing import Tuple, Dict, Any
from datetime import datetime
from decimal import Decimal

import pandas as pd

import sys

# Add project root to path for imports
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from config.constants import DataType, ImportStatus
from src.importer.base import BaseImporter, ImportResult
from src.validator.data_validator import DataValidator
from src.database.connection import get_db_manager
from src.database.models import (
    Product, Warehouse, Supplier, InventoryLevel, SalesRecord, ImportLog
)


class CSVImporter(BaseImporter):
    """Import data from CSV files."""

    def __init__(self, data_type: DataType):
        """
        Initialize CSV importer.

        Args:
            data_type: Type of data being imported
        """
        super().__init__(data_type)
        self.validator = DataValidator(data_type)
        self.db_manager = get_db_manager()

    def read_file(self, file_path: Path) -> pd.DataFrame:
        """
        Read CSV file into DataFrame.

        Args:
            file_path: Path to CSV file

        Returns:
            DataFrame with file contents
        """
        self.logger.info(f"Reading CSV file: {file_path}")

        # Try different encodings
        encodings = ["utf-8", "utf-8-sig", "latin-1", "cp1252", "iso-8859-1"]

        for encoding in encodings:
            try:
                df = pd.read_csv(
                    file_path,
                    encoding=encoding,
                    dtype=str,  # Read all as strings initially
                    na_values=["", "NA", "N/A", "null", "NULL", "None", "none"],
                    keep_default_na=True,
                    skipinitialspace=True
                )
                self.logger.debug(f"Successfully read file with {encoding} encoding")
                return df
            except UnicodeDecodeError:
                continue

        raise ValueError(f"Could not decode file with any supported encoding: {encodings}")

    def _process_data(self, df: pd.DataFrame) -> Tuple[int, int]:
        """
        Validate and save data to database.

        Args:
            df: DataFrame to process

        Returns:
            Tuple of (imported_count, failed_count)
        """
        # Validate all rows
        is_valid, errors, valid_df = self.validator.validate_dataframe(df)
        self.errors.extend(errors)

        failed = len(df) - len(valid_df)

        if valid_df.empty:
            self.logger.warning("No valid records to import")
            return 0, failed

        # Save to database
        with self.db_manager.get_session() as session:
            try:
                imported = self._save_to_database(session, valid_df)
                self._log_import(session, df, imported, failed)
                self.logger.info(f"Successfully imported {imported} records")
                return imported, failed
            except Exception as e:
                self.logger.error(f"Database save failed: {e}")
                self.errors.append({
                    "type": "database_error",
                    "message": str(e)
                })
                return 0, len(df)

    def _save_to_database(self, session, df: pd.DataFrame) -> int:
        """
        Save DataFrame records to appropriate table.

        Args:
            session: Database session
            df: DataFrame with validated records

        Returns:
            Number of records saved
        """
        model_map = {
            DataType.PRODUCTS: Product,
            DataType.WAREHOUSES: Warehouse,
            DataType.SUPPLIERS: Supplier,
            DataType.INVENTORY: InventoryLevel,
            DataType.SALES: SalesRecord,
        }

        model_class = model_map[self.data_type]
        records = df.to_dict("records")

        count = 0
        for record in records:
            try:
                converted = self._convert_record_types(record)
                instance = model_class(**converted)
                session.merge(instance)  # Use merge for upsert behavior
                count += 1
            except Exception as e:
                self.logger.warning(f"Failed to save record: {e}")
                self.errors.append({
                    "type": "record_save_error",
                    "message": str(e),
                    "record": record
                })

        return count

    def _convert_record_types(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convert string values to appropriate Python types.

        Args:
            record: Dictionary with string values

        Returns:
            Dictionary with converted types
        """
        type_converters = {
            "unit_cost": self._to_decimal,
            "unit_price": self._to_decimal,
            "revenue": self._to_decimal,
            "quantity": self._to_int,
            "quantity_sold": self._to_int,
            "capacity": self._to_int,
            "lead_time_days": self._to_int,
            "min_order_qty": self._to_int,
            "date": self._to_date,
            "last_updated": self._to_datetime,
        }

        converted = {}
        for key, value in record.items():
            if pd.isna(value):
                converted[key] = None
                continue

            if key in type_converters:
                try:
                    converted[key] = type_converters[key](value)
                except (ValueError, TypeError) as e:
                    self.logger.warning(f"Type conversion failed for {key}={value}: {e}")
                    converted[key] = None
            else:
                # String fields - strip whitespace
                converted[key] = str(value).strip() if value else None

        return converted

    def _to_decimal(self, value: Any) -> Decimal:
        """Convert value to Decimal."""
        if pd.isna(value) or value is None:
            return None
        return Decimal(str(value).strip())

    def _to_int(self, value: Any) -> int:
        """Convert value to integer."""
        if pd.isna(value) or value is None:
            return 0
        return int(float(str(value).strip()))

    def _to_date(self, value: Any) -> datetime:
        """Convert value to date."""
        if pd.isna(value) or value is None:
            return None

        str_value = str(value).strip()

        # Try common date formats
        formats = ["%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y", "%Y/%m/%d"]
        for fmt in formats:
            try:
                return datetime.strptime(str_value, fmt).date()
            except ValueError:
                continue

        raise ValueError(f"Cannot parse date: {value}")

    def _to_datetime(self, value: Any) -> datetime:
        """Convert value to datetime."""
        if pd.isna(value) or value is None:
            return datetime.now()

        str_value = str(value).strip()

        # Try ISO format first
        try:
            return datetime.fromisoformat(str_value)
        except ValueError:
            pass

        # Try other formats
        formats = ["%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"]
        for fmt in formats:
            try:
                return datetime.strptime(str_value, fmt)
            except ValueError:
                continue

        return datetime.now()

    def _log_import(self, session, df: pd.DataFrame, imported: int, failed: int):
        """
        Log the import operation.

        Args:
            session: Database session
            df: Original DataFrame
            imported: Number of records imported
            failed: Number of records failed
        """
        if failed == 0:
            status = ImportStatus.SUCCESS.value
        elif imported > 0:
            status = ImportStatus.PARTIAL.value
        else:
            status = ImportStatus.FAILED.value

        error_details = None
        if self.errors:
            # Store first few errors as details
            error_details = str(self.errors[:5])

        log_entry = ImportLog(
            filename=getattr(self, '_current_filename', 'unknown'),
            data_type=self.data_type.value,
            records_total=len(df),
            records_imported=imported,
            records_failed=failed,
            status=status,
            error_details=error_details
        )

        session.add(log_entry)
