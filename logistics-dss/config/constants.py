"""
Business Constants for Logistics DSS
Validation rules and business logic constants.
"""

from enum import Enum
from typing import Dict, List


class DataType(Enum):
    """Enumeration of data types that can be imported."""
    PRODUCTS = "products"
    INVENTORY = "inventory"
    SALES = "sales"
    SUPPLIERS = "suppliers"
    WAREHOUSES = "warehouses"


# Required Columns per Data Type
REQUIRED_COLUMNS: Dict[DataType, List[str]] = {
    DataType.PRODUCTS: ["id", "name", "category", "unit_cost", "unit_price"],
    DataType.INVENTORY: ["product_id", "warehouse_id", "quantity", "last_updated"],
    DataType.SALES: ["date", "product_id", "warehouse_id", "quantity_sold", "revenue"],
    DataType.SUPPLIERS: ["id", "name", "lead_time_days", "min_order_qty"],
    DataType.WAREHOUSES: ["id", "name", "location", "capacity"],
}


# Column Type Mappings (for validation)
COLUMN_TYPES: Dict[str, str] = {
    # Products
    "id": "string",
    "name": "string",
    "category": "string",
    "unit_cost": "decimal",
    "unit_price": "decimal",

    # Inventory
    "product_id": "string",
    "warehouse_id": "string",
    "quantity": "integer",
    "last_updated": "datetime",

    # Sales
    "date": "date",
    "quantity_sold": "integer",
    "revenue": "decimal",

    # Suppliers
    "lead_time_days": "integer",
    "min_order_qty": "integer",

    # Warehouses
    "location": "string",
    "capacity": "integer",
}


# Validation Rules - Numeric Ranges
VALIDATION_RULES: Dict[str, Dict[str, float]] = {
    "unit_cost": {"min": 0, "max": 1_000_000},
    "unit_price": {"min": 0, "max": 1_000_000},
    "quantity": {"min": 0, "max": 10_000_000},
    "quantity_sold": {"min": 0, "max": 10_000_000},
    "revenue": {"min": 0, "max": 100_000_000},
    "lead_time_days": {"min": 0, "max": 365},
    "min_order_qty": {"min": 1, "max": 1_000_000},
    "capacity": {"min": 1, "max": 100_000_000},
}


# String Length Constraints
STRING_MAX_LENGTHS: Dict[str, int] = {
    "id": 50,
    "product_id": 50,
    "warehouse_id": 50,
    "name": 200,
    "category": 100,
    "location": 300,
}


# Import Status Values
class ImportStatus(Enum):
    """Status values for import operations."""
    SUCCESS = "success"
    PARTIAL = "partial"
    FAILED = "failed"


# KPI Configuration (Phase 2)
CARRYING_COST_RATE = 0.25  # Annual carrying cost as % of inventory value
DEFAULT_LOOKBACK_DAYS = 30  # Default period for sales-based KPIs
LOW_STOCK_THRESHOLD = 10  # Default "low stock" quantity threshold
STOCKOUT_THRESHOLD = 0  # Quantity at or below which product is "out"
DAYS_OF_SUPPLY_WARNING = 7  # Days of supply below which to flag warning
DAYS_OF_SUPPLY_CRITICAL = 3  # Days of supply below which to flag critical
TABLE_PAGE_SIZE = 50  # Rows per page in data tables

# Analytics Configuration (Phase 3)
ABC_A_THRESHOLD = 0.70  # Cumulative revenue cutoff for class A
ABC_B_THRESHOLD = 0.90  # Cumulative revenue cutoff for class A+B
DEFAULT_ANALYTICS_DAYS = 90  # Default sales lookback period for ABC analysis
