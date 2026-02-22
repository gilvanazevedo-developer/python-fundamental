"""
Excel File Importer
Handles importing data from Excel files (.xlsx, .xls).
"""

from pathlib import Path
from typing import Optional, List

import pandas as pd

import sys

# Add project root to path for imports
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from config.constants import DataType
from src.importer.csv_importer import CSVImporter


class ExcelImporter(CSVImporter):
    """
    Import data from Excel files.

    Extends CSVImporter for shared validation and database logic.
    """

    def __init__(self, data_type: DataType, sheet_name: Optional[str] = None):
        """
        Initialize Excel importer.

        Args:
            data_type: Type of data being imported
            sheet_name: Optional specific sheet to read (defaults to first sheet)
        """
        super().__init__(data_type)
        self.sheet_name = sheet_name

    def read_file(self, file_path: Path) -> pd.DataFrame:
        """
        Read Excel file into DataFrame.

        Args:
            file_path: Path to Excel file

        Returns:
            DataFrame with file contents
        """
        self.logger.info(f"Reading Excel file: {file_path}")

        try:
            # Determine engine based on file extension
            suffix = file_path.suffix.lower()
            engine = "openpyxl" if suffix == ".xlsx" else "xlrd"

            # Read Excel file
            df = pd.read_excel(
                file_path,
                sheet_name=self.sheet_name or 0,  # Default to first sheet
                dtype=str,  # Read all as strings initially
                na_values=["", "NA", "N/A", "null", "NULL", "None", "none"],
                keep_default_na=True,
                engine=engine
            )

            self.logger.info(f"Read {len(df)} rows from Excel file")
            return df

        except Exception as e:
            self.logger.error(f"Failed to read Excel file: {e}")
            raise

    def get_sheet_names(self, file_path: Path) -> List[str]:
        """
        Get list of sheet names in Excel file.

        Args:
            file_path: Path to Excel file

        Returns:
            List of sheet names
        """
        suffix = Path(file_path).suffix.lower()
        engine = "openpyxl" if suffix == ".xlsx" else "xlrd"

        xl = pd.ExcelFile(file_path, engine=engine)
        return xl.sheet_names

    def import_sheet(self, file_path: Path, sheet_name: str) -> 'ImportResult':
        """
        Import a specific sheet from an Excel file.

        Args:
            file_path: Path to Excel file
            sheet_name: Name of sheet to import

        Returns:
            ImportResult for this sheet
        """
        self.sheet_name = sheet_name
        return self.import_file(file_path)

    def import_all_sheets(self, file_path: Path) -> List['ImportResult']:
        """
        Import all sheets from an Excel file.

        Args:
            file_path: Path to Excel file

        Returns:
            List of ImportResult objects, one per sheet
        """
        results = []
        sheet_names = self.get_sheet_names(file_path)

        self.logger.info(f"Found {len(sheet_names)} sheets: {sheet_names}")

        for sheet in sheet_names:
            self.logger.info(f"Importing sheet: {sheet}")
            result = self.import_sheet(file_path, sheet)
            results.append(result)

        return results
