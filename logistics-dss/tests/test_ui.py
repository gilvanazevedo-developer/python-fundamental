"""
Tests for UI Components (non-visual logic)
"""

import pytest
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.ui.theme import format_number, format_currency, format_percentage


class TestFormatNumber:
    """Tests for number formatting functions."""

    def test_format_integer(self):
        assert format_number(1234) == "1,234"

    def test_format_large_number(self):
        assert format_number(1234567) == "1,234,567"

    def test_format_zero(self):
        assert format_number(0) == "0"

    def test_format_with_decimals(self):
        assert format_number(1234.56, decimals=2) == "1,234.56"

    def test_format_none(self):
        assert format_number(None) == "N/A"


class TestFormatCurrency:
    """Tests for currency formatting."""

    def test_format_millions(self):
        assert format_currency(1500000) == "$1.5M"

    def test_format_thousands(self):
        assert format_currency(42500) == "$42.5K"

    def test_format_small(self):
        assert format_currency(99.50) == "$99.50"

    def test_format_none(self):
        assert format_currency(None) == "N/A"

    def test_format_zero(self):
        assert format_currency(0) == "$0.00"


class TestFormatPercentage:
    """Tests for percentage formatting."""

    def test_format_percentage(self):
        assert format_percentage(42.5) == "42.5%"

    def test_format_zero_percent(self):
        assert format_percentage(0) == "0.0%"

    def test_format_hundred_percent(self):
        assert format_percentage(100) == "100.0%"

    def test_format_none(self):
        assert format_percentage(None) == "N/A"
