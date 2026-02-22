"""
Data Validator
Main validation class for imported data.
"""

from typing import Dict, Any, List, Tuple
import pandas as pd

import sys
from pathlib import Path

# Add project root to path for imports
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from config.constants import DataType, REQUIRED_COLUMNS, COLUMN_TYPES
from config.settings import MAX_VALIDATION_ERRORS
from src.validator.rules import (
    RequiredRule, StringLengthRule, NumericRangeRule,
    DecimalRule, IntegerRule, DateRule, DateTimeRule
)
from src.logger import LoggerMixin


class DataValidator(LoggerMixin):
    """Validates data rows based on data type rules."""

    def __init__(self, data_type: DataType):
        """
        Initialize validator for specific data type.

        Args:
            data_type: Type of data being validated
        """
        self.data_type = data_type
        self.required_fields = REQUIRED_COLUMNS[data_type]
        self.rules = self._build_rules()

    def _build_rules(self) -> Dict[str, List]:
        """
        Build validation rules based on data type.

        Returns:
            Dictionary mapping field names to list of rules
        """
        rules = {}

        for field in self.required_fields:
            field_rules = []

            # Add required rule
            field_rules.append(RequiredRule(field))

            # Add type-specific rules
            field_type = COLUMN_TYPES.get(field, "string")

            if field_type == "string":
                field_rules.append(StringLengthRule(field))
            elif field_type == "decimal":
                field_rules.append(DecimalRule(field))
                field_rules.append(NumericRangeRule(field))
            elif field_type == "integer":
                field_rules.append(IntegerRule(field))
                field_rules.append(NumericRangeRule(field))
            elif field_type == "date":
                field_rules.append(DateRule(field))
            elif field_type == "datetime":
                field_rules.append(DateTimeRule(field))

            rules[field] = field_rules

        return rules

    def validate_row(
        self,
        row: Dict[str, Any],
        row_index: int = None
    ) -> Tuple[bool, List[Dict[str, Any]]]:
        """
        Validate a single row of data.

        Args:
            row: Dictionary of field -> value
            row_index: Optional row index for error reporting

        Returns:
            Tuple of (is_valid, list of error dicts)
        """
        errors = []
        row_prefix = f"Row {row_index}: " if row_index is not None else ""

        for field, field_rules in self.rules.items():
            value = row.get(field)

            for rule in field_rules:
                is_valid, error_msg = rule.validate(value)

                if not is_valid:
                    errors.append({
                        "row": row_index,
                        "field": field,
                        "value": value,
                        "message": f"{row_prefix}{error_msg}"
                    })
                    # Stop checking other rules for this field after first error
                    break

        if errors:
            self.logger.debug(f"Row {row_index} validation failed: {len(errors)} errors")

        return len(errors) == 0, errors

    def validate_dataframe(
        self,
        df: pd.DataFrame,
        max_errors: int = None
    ) -> Tuple[bool, List[Dict], pd.DataFrame]:
        """
        Validate an entire DataFrame.

        Args:
            df: Pandas DataFrame to validate
            max_errors: Maximum errors to collect before stopping

        Returns:
            Tuple of (all_valid, list of errors, valid_rows_df)
        """
        max_errors = max_errors or MAX_VALIDATION_ERRORS
        all_errors = []
        valid_indices = []

        for idx, row in df.iterrows():
            is_valid, row_errors = self.validate_row(row.to_dict(), idx)

            if is_valid:
                valid_indices.append(idx)
            else:
                all_errors.extend(row_errors)

            if len(all_errors) >= max_errors:
                self.logger.warning(f"Stopped validation after {max_errors} errors")
                break

        valid_df = df.loc[valid_indices] if valid_indices else pd.DataFrame()

        self.logger.info(
            f"Validation complete: {len(df)} rows, "
            f"{len(valid_indices)} valid, {len(all_errors)} errors"
        )

        return len(all_errors) == 0, all_errors, valid_df

    def get_validation_summary(self, errors: List[Dict]) -> Dict[str, Any]:
        """
        Generate a summary of validation errors.

        Args:
            errors: List of error dictionaries

        Returns:
            Summary dictionary with error counts by field
        """
        summary = {
            "total_errors": len(errors),
            "errors_by_field": {},
            "sample_errors": errors[:5]  # First 5 errors as samples
        }

        for error in errors:
            field = error.get("field", "unknown")
            if field not in summary["errors_by_field"]:
                summary["errors_by_field"][field] = 0
            summary["errors_by_field"][field] += 1

        return summary
