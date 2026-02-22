"""
Tests for Data Validation Module
"""

import pytest
import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from config.constants import DataType
from src.validator.rules import (
    RequiredRule, StringLengthRule, NumericRangeRule,
    DecimalRule, IntegerRule, DateRule, DateTimeRule
)
from src.validator.data_validator import DataValidator


class TestRequiredRule:
    """Tests for RequiredRule."""

    def test_valid_string(self):
        rule = RequiredRule("name")
        is_valid, error = rule.validate("Test Value")
        assert is_valid is True
        assert error is None

    def test_empty_string(self):
        rule = RequiredRule("name")
        is_valid, error = rule.validate("")
        assert is_valid is False
        assert "required" in error.lower()

    def test_none_value(self):
        rule = RequiredRule("name")
        is_valid, error = rule.validate(None)
        assert is_valid is False
        assert "required" in error.lower()

    def test_whitespace_only(self):
        rule = RequiredRule("name")
        is_valid, error = rule.validate("   ")
        assert is_valid is False


class TestStringLengthRule:
    """Tests for StringLengthRule."""

    def test_valid_length(self):
        rule = StringLengthRule("id", max_length=50)
        is_valid, error = rule.validate("SKU001")
        assert is_valid is True

    def test_exceeds_max_length(self):
        rule = StringLengthRule("id", max_length=5)
        is_valid, error = rule.validate("SKU001234567890")
        assert is_valid is False
        assert "exceeds" in error.lower()

    def test_none_value_allowed(self):
        rule = StringLengthRule("id", max_length=50)
        is_valid, error = rule.validate(None)
        assert is_valid is True


class TestNumericRangeRule:
    """Tests for NumericRangeRule."""

    def test_valid_in_range(self):
        rule = NumericRangeRule("quantity", min_val=0, max_val=1000)
        is_valid, error = rule.validate("500")
        assert is_valid is True

    def test_below_minimum(self):
        rule = NumericRangeRule("quantity", min_val=0, max_val=1000)
        is_valid, error = rule.validate("-10")
        assert is_valid is False
        assert ">=" in error

    def test_above_maximum(self):
        rule = NumericRangeRule("quantity", min_val=0, max_val=1000)
        is_valid, error = rule.validate("2000")
        assert is_valid is False
        assert "<=" in error

    def test_invalid_number(self):
        rule = NumericRangeRule("quantity", min_val=0, max_val=1000)
        is_valid, error = rule.validate("not_a_number")
        assert is_valid is False
        assert "valid number" in error.lower()


class TestDecimalRule:
    """Tests for DecimalRule."""

    def test_valid_decimal(self):
        rule = DecimalRule("unit_cost")
        is_valid, error = rule.validate("19.99")
        assert is_valid is True

    def test_valid_integer_as_decimal(self):
        rule = DecimalRule("unit_cost")
        is_valid, error = rule.validate("100")
        assert is_valid is True

    def test_invalid_decimal(self):
        rule = DecimalRule("unit_cost")
        is_valid, error = rule.validate("abc")
        assert is_valid is False
        assert "decimal" in error.lower()


class TestIntegerRule:
    """Tests for IntegerRule."""

    def test_valid_integer(self):
        rule = IntegerRule("quantity")
        is_valid, error = rule.validate("100")
        assert is_valid is True

    def test_float_string_whole(self):
        rule = IntegerRule("quantity")
        is_valid, error = rule.validate("100.0")
        assert is_valid is True

    def test_float_string_fractional(self):
        rule = IntegerRule("quantity")
        is_valid, error = rule.validate("100.5")
        assert is_valid is False
        assert "whole number" in error.lower()

    def test_invalid_integer(self):
        rule = IntegerRule("quantity")
        is_valid, error = rule.validate("abc")
        assert is_valid is False


class TestDateRule:
    """Tests for DateRule."""

    def test_valid_iso_date(self):
        rule = DateRule("date")
        is_valid, error = rule.validate("2024-01-15")
        assert is_valid is True

    def test_valid_slash_date(self):
        rule = DateRule("date")
        is_valid, error = rule.validate("15/01/2024")
        assert is_valid is True

    def test_invalid_date(self):
        rule = DateRule("date")
        is_valid, error = rule.validate("not-a-date")
        assert is_valid is False
        assert "valid date" in error.lower()


class TestDateTimeRule:
    """Tests for DateTimeRule."""

    def test_valid_iso_datetime(self):
        rule = DateTimeRule("last_updated")
        is_valid, error = rule.validate("2024-01-15T10:30:00")
        assert is_valid is True

    def test_valid_datetime_with_space(self):
        rule = DateTimeRule("last_updated")
        is_valid, error = rule.validate("2024-01-15 10:30:00")
        assert is_valid is True

    def test_invalid_datetime(self):
        rule = DateTimeRule("last_updated")
        is_valid, error = rule.validate("not-a-datetime")
        assert is_valid is False


class TestDataValidator:
    """Tests for DataValidator class."""

    def test_validate_valid_product_row(self, valid_product_row):
        validator = DataValidator(DataType.PRODUCTS)
        is_valid, errors = validator.validate_row(valid_product_row, 0)
        assert is_valid is True
        assert len(errors) == 0

    def test_validate_invalid_product_row(self, invalid_product_row):
        validator = DataValidator(DataType.PRODUCTS)
        is_valid, errors = validator.validate_row(invalid_product_row, 0)
        assert is_valid is False
        assert len(errors) > 0

    def test_validate_dataframe(self, sample_products_df):
        validator = DataValidator(DataType.PRODUCTS)
        is_valid, errors, valid_df = validator.validate_dataframe(sample_products_df)
        assert is_valid is True
        assert len(errors) == 0
        assert len(valid_df) == 3

    def test_validation_summary(self):
        validator = DataValidator(DataType.PRODUCTS)
        errors = [
            {"field": "name", "message": "Error 1"},
            {"field": "name", "message": "Error 2"},
            {"field": "unit_cost", "message": "Error 3"},
        ]
        summary = validator.get_validation_summary(errors)
        assert summary["total_errors"] == 3
        assert summary["errors_by_field"]["name"] == 2
        assert summary["errors_by_field"]["unit_cost"] == 1
