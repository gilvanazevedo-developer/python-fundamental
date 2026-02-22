"""
Validation Rules
Defines validation rules for different data types.
"""

from typing import Any, Tuple, Optional
from decimal import Decimal, InvalidOperation
from datetime import datetime, date
import re

import sys
from pathlib import Path

# Add project root to path for imports
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from config.constants import VALIDATION_RULES, STRING_MAX_LENGTHS


class ValidationRule:
    """Base class for validation rules."""

    def __init__(self, field_name: str, message: str = None):
        """
        Initialize validation rule.

        Args:
            field_name: Name of the field being validated
            message: Optional custom error message
        """
        self.field_name = field_name
        self.message = message

    def validate(self, value: Any) -> Tuple[bool, Optional[str]]:
        """
        Validate a value.

        Args:
            value: Value to validate

        Returns:
            Tuple of (is_valid, error_message)
        """
        raise NotImplementedError("Subclasses must implement validate()")


class RequiredRule(ValidationRule):
    """Value must not be null/empty."""

    def validate(self, value: Any) -> Tuple[bool, Optional[str]]:
        """Check if value is present and not empty."""
        if value is None:
            return False, self.message or f"{self.field_name} is required"

        if isinstance(value, str) and not value.strip():
            return False, self.message or f"{self.field_name} is required"

        return True, None


class StringLengthRule(ValidationRule):
    """String must not exceed max length."""

    def __init__(self, field_name: str, max_length: int = None):
        """
        Initialize string length rule.

        Args:
            field_name: Name of the field
            max_length: Maximum allowed length (defaults to constants)
        """
        super().__init__(field_name)
        self.max_length = max_length or STRING_MAX_LENGTHS.get(field_name, 255)

    def validate(self, value: Any) -> Tuple[bool, Optional[str]]:
        """Check if string length is within limit."""
        if value is None:
            return True, None

        if len(str(value)) > self.max_length:
            return False, f"{self.field_name} exceeds maximum length of {self.max_length}"

        return True, None


class NumericRangeRule(ValidationRule):
    """Numeric value must be within range."""

    def __init__(self, field_name: str, min_val: float = None, max_val: float = None):
        """
        Initialize numeric range rule.

        Args:
            field_name: Name of the field
            min_val: Minimum allowed value
            max_val: Maximum allowed value
        """
        super().__init__(field_name)
        rules = VALIDATION_RULES.get(field_name, {})
        self.min_val = min_val if min_val is not None else rules.get("min")
        self.max_val = max_val if max_val is not None else rules.get("max")

    def validate(self, value: Any) -> Tuple[bool, Optional[str]]:
        """Check if numeric value is within range."""
        if value is None:
            return True, None

        try:
            num_value = float(value)
        except (ValueError, TypeError):
            return False, f"{self.field_name} must be a valid number"

        if self.min_val is not None and num_value < self.min_val:
            return False, f"{self.field_name} must be >= {self.min_val}"

        if self.max_val is not None and num_value > self.max_val:
            return False, f"{self.field_name} must be <= {self.max_val}"

        return True, None


class DecimalRule(ValidationRule):
    """Value must be a valid decimal number."""

    def validate(self, value: Any) -> Tuple[bool, Optional[str]]:
        """Check if value is a valid decimal."""
        if value is None:
            return True, None

        try:
            Decimal(str(value))
            return True, None
        except (InvalidOperation, ValueError):
            return False, f"{self.field_name} must be a valid decimal number"


class IntegerRule(ValidationRule):
    """Value must be a valid integer."""

    def validate(self, value: Any) -> Tuple[bool, Optional[str]]:
        """Check if value is a valid integer."""
        if value is None:
            return True, None

        try:
            # Handle float strings like "100.0"
            float_val = float(value)
            if float_val != int(float_val):
                return False, f"{self.field_name} must be a whole number"
            return True, None
        except (ValueError, TypeError):
            return False, f"{self.field_name} must be a valid integer"


class DateRule(ValidationRule):
    """Value must be a valid date."""

    DATE_FORMATS = [
        "%Y-%m-%d",      # 2024-01-15
        "%d/%m/%Y",      # 15/01/2024
        "%m/%d/%Y",      # 01/15/2024
        "%Y/%m/%d",      # 2024/01/15
        "%d-%m-%Y",      # 15-01-2024
    ]

    def validate(self, value: Any) -> Tuple[bool, Optional[str]]:
        """Check if value is a valid date."""
        if value is None:
            return True, None

        # Already a date object
        if isinstance(value, (date, datetime)):
            return True, None

        # Try parsing string
        str_value = str(value).strip()

        for fmt in self.DATE_FORMATS:
            try:
                datetime.strptime(str_value, fmt)
                return True, None
            except ValueError:
                continue

        return False, f"{self.field_name} must be a valid date (YYYY-MM-DD)"


class DateTimeRule(ValidationRule):
    """Value must be a valid datetime."""

    DATETIME_FORMATS = [
        "%Y-%m-%dT%H:%M:%S",      # ISO format
        "%Y-%m-%d %H:%M:%S",       # Standard format
        "%Y-%m-%dT%H:%M:%S.%f",    # ISO with microseconds
        "%Y-%m-%d %H:%M:%S.%f",    # Standard with microseconds
        "%Y-%m-%d",                # Date only
    ]

    def validate(self, value: Any) -> Tuple[bool, Optional[str]]:
        """Check if value is a valid datetime."""
        if value is None:
            return True, None

        # Already a datetime object
        if isinstance(value, datetime):
            return True, None

        # Try ISO format first
        str_value = str(value).strip()

        try:
            datetime.fromisoformat(str_value)
            return True, None
        except ValueError:
            pass

        # Try other formats
        for fmt in self.DATETIME_FORMATS:
            try:
                datetime.strptime(str_value, fmt)
                return True, None
            except ValueError:
                continue

        return False, f"{self.field_name} must be a valid datetime"


class PatternRule(ValidationRule):
    """Value must match a regex pattern."""

    def __init__(self, field_name: str, pattern: str, message: str = None):
        """
        Initialize pattern rule.

        Args:
            field_name: Name of the field
            pattern: Regex pattern to match
            message: Custom error message
        """
        super().__init__(field_name, message)
        self.pattern = re.compile(pattern)

    def validate(self, value: Any) -> Tuple[bool, Optional[str]]:
        """Check if value matches pattern."""
        if value is None:
            return True, None

        if not self.pattern.match(str(value)):
            return False, self.message or f"{self.field_name} has invalid format"

        return True, None


class UniqueRule(ValidationRule):
    """Value must be unique (checked against provided set)."""

    def __init__(self, field_name: str, existing_values: set = None):
        """
        Initialize unique rule.

        Args:
            field_name: Name of the field
            existing_values: Set of existing values to check against
        """
        super().__init__(field_name)
        self.existing_values = existing_values or set()

    def validate(self, value: Any) -> Tuple[bool, Optional[str]]:
        """Check if value is unique."""
        if value is None:
            return True, None

        if value in self.existing_values:
            return False, f"{self.field_name} '{value}' already exists"

        return True, None

    def add_value(self, value: Any):
        """Add a value to the existing values set."""
        self.existing_values.add(value)
