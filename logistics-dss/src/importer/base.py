"""
Base Importer Class
Abstract base class for data importers.
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, Any, List, Tuple
from dataclasses import dataclass, field
from datetime import datetime

import pandas as pd

import sys

# Add project root to path for imports
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from config.constants import DataType, REQUIRED_COLUMNS
from src.logger import LoggerMixin


@dataclass
class ImportResult:
    """Result of an import operation."""
    success: bool
    data_type: DataType
    filename: str
    total_records: int
    imported_records: int
    failed_records: int
    errors: List[Dict[str, Any]] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    duration_seconds: float = 0.0

    @property
    def summary(self) -> str:
        """Generate a human-readable summary."""
        status = "succeeded" if self.success else "failed"
        return (
            f"Import {status}: "
            f"{self.imported_records}/{self.total_records} records imported, "
            f"{self.failed_records} failed"
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for logging/storage."""
        return {
            "success": self.success,
            "data_type": self.data_type.value,
            "filename": self.filename,
            "total_records": self.total_records,
            "imported_records": self.imported_records,
            "failed_records": self.failed_records,
            "error_count": len(self.errors),
            "warning_count": len(self.warnings),
            "duration_seconds": self.duration_seconds
        }


class BaseImporter(ABC, LoggerMixin):
    """Abstract base class for file importers."""

    def __init__(self, data_type: DataType):
        """
        Initialize importer.

        Args:
            data_type: Type of data being imported
        """
        self.data_type = data_type
        self.required_columns = REQUIRED_COLUMNS[data_type]
        self.errors: List[Dict[str, Any]] = []
        self.warnings: List[str] = []

    @abstractmethod
    def read_file(self, file_path: Path) -> pd.DataFrame:
        """
        Read file and return DataFrame.

        Args:
            file_path: Path to the file to read

        Returns:
            DataFrame with file contents

        Must be implemented by subclasses.
        """
        pass

    def validate_file(self, file_path: Path) -> bool:
        """
        Validate that file exists and is readable.

        Args:
            file_path: Path to validate

        Returns:
            True if file is valid
        """
        if not file_path.exists():
            self.errors.append({
                "type": "file_not_found",
                "message": f"File not found: {file_path}"
            })
            return False

        if not file_path.is_file():
            self.errors.append({
                "type": "not_a_file",
                "message": f"Path is not a file: {file_path}"
            })
            return False

        return True

    def validate_columns(self, df: pd.DataFrame) -> bool:
        """
        Validate that required columns are present.

        Args:
            df: DataFrame to validate

        Returns:
            True if valid, False otherwise
        """
        self.logger.debug(f"Validating columns for {self.data_type.value}")

        df_columns = [col.lower().strip() for col in df.columns]
        missing = [col for col in self.required_columns if col not in df_columns]

        if missing:
            self.errors.append({
                "type": "missing_columns",
                "message": f"Missing required columns: {missing}",
                "columns": missing,
                "found_columns": list(df.columns)
            })
            return False

        return True

    def normalize_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Normalize column names (lowercase, strip whitespace).

        Args:
            df: DataFrame with columns to normalize

        Returns:
            DataFrame with normalized column names
        """
        df = df.copy()
        df.columns = [col.lower().strip() for col in df.columns]
        return df

    def import_file(self, file_path: Path) -> ImportResult:
        """
        Main import method.

        Args:
            file_path: Path to file to import

        Returns:
            ImportResult with details of the import operation
        """
        start_time = datetime.now()
        self.errors = []
        self.warnings = []

        file_path = Path(file_path)
        filename = file_path.name

        self.logger.info(f"Starting import: {filename} as {self.data_type.value}")

        # Validate file exists
        if not self.validate_file(file_path):
            duration = (datetime.now() - start_time).total_seconds()
            return ImportResult(
                success=False,
                data_type=self.data_type,
                filename=filename,
                total_records=0,
                imported_records=0,
                failed_records=0,
                errors=self.errors,
                warnings=self.warnings,
                duration_seconds=duration
            )

        try:
            # Read file
            df = self.read_file(file_path)
            total_records = len(df)
            self.logger.info(f"Read {total_records} records from file")

            if total_records == 0:
                self.warnings.append("File contains no data records")
                duration = (datetime.now() - start_time).total_seconds()
                return ImportResult(
                    success=True,
                    data_type=self.data_type,
                    filename=filename,
                    total_records=0,
                    imported_records=0,
                    failed_records=0,
                    errors=self.errors,
                    warnings=self.warnings,
                    duration_seconds=duration
                )

            # Normalize columns
            df = self.normalize_columns(df)

            # Validate columns
            if not self.validate_columns(df):
                duration = (datetime.now() - start_time).total_seconds()
                return ImportResult(
                    success=False,
                    data_type=self.data_type,
                    filename=filename,
                    total_records=total_records,
                    imported_records=0,
                    failed_records=total_records,
                    errors=self.errors,
                    warnings=self.warnings,
                    duration_seconds=duration
                )

            # Process and validate data
            imported, failed = self._process_data(df)

            duration = (datetime.now() - start_time).total_seconds()

            success = failed == 0 or imported > 0

            return ImportResult(
                success=success,
                data_type=self.data_type,
                filename=filename,
                total_records=total_records,
                imported_records=imported,
                failed_records=failed,
                errors=self.errors,
                warnings=self.warnings,
                duration_seconds=duration
            )

        except Exception as e:
            self.logger.error(f"Import failed: {e}")
            duration = (datetime.now() - start_time).total_seconds()
            return ImportResult(
                success=False,
                data_type=self.data_type,
                filename=filename,
                total_records=0,
                imported_records=0,
                failed_records=0,
                errors=[{"type": "exception", "message": str(e)}],
                warnings=self.warnings,
                duration_seconds=duration
            )

    @abstractmethod
    def _process_data(self, df: pd.DataFrame) -> Tuple[int, int]:
        """
        Process and save data to database.

        Args:
            df: Validated DataFrame

        Returns:
            Tuple of (imported_count, failed_count)
        """
        pass
