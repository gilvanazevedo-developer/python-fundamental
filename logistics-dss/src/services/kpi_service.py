"""
KPI Service
Compute all dashboard KPIs from inventory and sales data.
"""

from typing import Dict, Any, Optional

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from config.constants import (
    CARRYING_COST_RATE,
    DEFAULT_LOOKBACK_DAYS,
    LOW_STOCK_THRESHOLD,
)
from src.database.connection import get_db_manager
from src.services.inventory_service import InventoryService
from src.services.sales_service import SalesService
from src.logger import LoggerMixin


class KPIService(LoggerMixin):
    """Compute all dashboard KPIs."""

    def __init__(self, db_manager=None):
        self.db_manager = db_manager or get_db_manager()
        self.inventory_service = InventoryService(self.db_manager)
        self.sales_service = SalesService(self.db_manager)

    def get_stock_health_kpis(
        self,
        category: Optional[str] = None,
        warehouse_id: Optional[str] = None,
        days: int = None,
    ) -> Dict[str, Any]:
        """Compute stock health KPIs."""
        days = days or DEFAULT_LOOKBACK_DAYS

        summary = self.inventory_service.get_stock_summary(
            category=category, warehouse_id=warehouse_id
        )
        total_products = summary["total_products"]
        total_units = summary["total_units"]
        total_value = summary["total_value"]

        # Average daily demand (total across all products)
        total_sold = self.sales_service.get_total_quantity_sold(
            days=days, category=category
        )
        avg_daily_demand = total_sold / days if days > 0 else 0.0

        # Days of supply
        days_of_supply = (
            total_units / avg_daily_demand if avg_daily_demand > 0 else float("inf")
        )

        # Inventory turnover (annualized)
        # COGS sold in period / average inventory value
        # Approximate: use current value as average
        total_revenue = self.sales_service.get_total_revenue(
            days=days, category=category
        )
        # Approximate COGS as revenue * cost_ratio if we have both values
        if summary["total_retail_value"] > 0:
            cost_ratio = total_value / summary["total_retail_value"]
        else:
            cost_ratio = 0.5  # default fallback
        cogs_sold = total_revenue * cost_ratio

        turnover = cogs_sold / total_value if total_value > 0 else 0.0
        # Annualize
        annualized_turnover = turnover * (365 / days) if days > 0 else 0.0

        return {
            "total_products": total_products,
            "total_units": total_units,
            "days_of_supply": round(days_of_supply, 1) if days_of_supply != float("inf") else None,
            "avg_daily_demand": round(avg_daily_demand, 1),
            "inventory_turnover": round(annualized_turnover, 2),
        }

    def get_service_level_kpis(
        self,
        category: Optional[str] = None,
        warehouse_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Compute service level KPIs."""
        summary = self.inventory_service.get_stock_summary(
            category=category, warehouse_id=warehouse_id
        )
        total_products = summary["total_products"]
        stockout_count = summary["stockout_count"]
        products_with_stock = summary["products_with_stock"]

        stockout_rate = (
            (stockout_count / total_products * 100) if total_products > 0 else 0.0
        )

        # Fill rate approximation (products with stock / total)
        fill_rate = (
            (products_with_stock / total_products * 100) if total_products > 0 else 0.0
        )

        # Low stock count
        low_stock_items = self.inventory_service.get_low_stock_items(
            threshold=LOW_STOCK_THRESHOLD, category=category
        )
        low_stock_count = len([i for i in low_stock_items if i["status"] == "LOW STOCK"])

        return {
            "stockout_count": stockout_count,
            "stockout_rate": round(stockout_rate, 1),
            "fill_rate": round(fill_rate, 1),
            "low_stock_count": low_stock_count,
        }

    def get_financial_kpis(
        self,
        category: Optional[str] = None,
        warehouse_id: Optional[str] = None,
        days: int = None,
    ) -> Dict[str, Any]:
        """Compute financial KPIs."""
        days = days or DEFAULT_LOOKBACK_DAYS

        summary = self.inventory_service.get_stock_summary(
            category=category, warehouse_id=warehouse_id
        )
        total_value = summary["total_value"]
        total_retail_value = summary["total_retail_value"]
        total_units = summary["total_units"]

        # Carrying cost (monthly)
        carrying_cost_monthly = total_value * CARRYING_COST_RATE / 12
        carrying_cost_annual = total_value * CARRYING_COST_RATE

        # Average unit cost
        avg_unit_cost = total_value / total_units if total_units > 0 else 0.0

        # Potential margin
        potential_margin = total_retail_value - total_value

        # Revenue in period
        revenue = self.sales_service.get_total_revenue(days=days, category=category)

        return {
            "total_inventory_value": round(total_value, 2),
            "total_retail_value": round(total_retail_value, 2),
            "carrying_cost_monthly": round(carrying_cost_monthly, 2),
            "carrying_cost_annual": round(carrying_cost_annual, 2),
            "avg_unit_cost": round(avg_unit_cost, 2),
            "potential_margin": round(potential_margin, 2),
            "revenue_period": round(revenue, 2),
        }

    def get_all_kpis(
        self,
        category: Optional[str] = None,
        warehouse_id: Optional[str] = None,
        days: int = None,
    ) -> Dict[str, Any]:
        """Get all KPIs combined."""
        return {
            "stock_health": self.get_stock_health_kpis(category, warehouse_id, days),
            "service_level": self.get_service_level_kpis(category, warehouse_id),
            "financial": self.get_financial_kpis(category, warehouse_id, days),
        }

    def get_product_kpis(
        self, product_id: str, days: int = None
    ) -> Dict[str, Any]:
        """Get KPIs for a single product."""
        days = days or DEFAULT_LOOKBACK_DAYS

        stock_data = self.inventory_service.get_stock_by_product(product_id)
        total_stock = sum(s["quantity"] for s in stock_data)

        avg_daily_demand = self.sales_service.get_average_daily_demand(
            product_id, days=days
        )
        days_of_supply = (
            total_stock / avg_daily_demand if avg_daily_demand > 0 else None
        )

        return {
            "product_id": product_id,
            "total_stock": total_stock,
            "warehouse_count": len(stock_data),
            "avg_daily_demand": round(avg_daily_demand, 2),
            "days_of_supply": round(days_of_supply, 1) if days_of_supply else None,
            "warehouses": stock_data,
        }
