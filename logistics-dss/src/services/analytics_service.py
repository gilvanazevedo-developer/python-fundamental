"""
Analytics Service
Computes ABC classification and inventory turnover from live database data.
"""

from typing import Dict, Any, List, Optional
from datetime import date, timedelta

from sqlalchemy import func

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.database.connection import get_db_manager
from src.database.models import Product, InventoryLevel, SalesRecord
from src.analytics.abc_analysis import classify, summarize, ABCItem
from src.logger import LoggerMixin
from config.constants import ABC_A_THRESHOLD, ABC_B_THRESHOLD, DEFAULT_ANALYTICS_DAYS


class AnalyticsService(LoggerMixin):
    """Provides ABC classification and inventory turnover analytics."""

    def __init__(self, db_manager=None):
        self.db_manager = db_manager or get_db_manager()

    def _lookback_date(self, days: int) -> date:
        """Calculate the start date for a lookback period."""
        return date.today() - timedelta(days=days)

    def _get_product_revenue(
        self,
        days: int,
        category: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Aggregate total revenue and quantity sold per product for the period."""
        start = self._lookback_date(days)

        with self.db_manager.get_session() as session:
            query = (
                session.query(
                    Product.id.label("product_id"),
                    Product.name.label("product_name"),
                    Product.category,
                    func.coalesce(func.sum(SalesRecord.revenue), 0).label("total_revenue"),
                    func.coalesce(func.sum(SalesRecord.quantity_sold), 0).label("total_quantity"),
                )
                .outerjoin(
                    SalesRecord,
                    (SalesRecord.product_id == Product.id)
                    & (SalesRecord.date >= start),
                )
                .group_by(Product.id)
            )

            if category:
                query = query.filter(Product.category == category)

            rows = query.all()

            return [
                {
                    "product_id": r.product_id,
                    "product_name": r.product_name,
                    "category": r.category,
                    "total_revenue": float(r.total_revenue),
                    "total_quantity": int(r.total_quantity),
                }
                for r in rows
            ]

    def _get_stock_map(self, category: Optional[str] = None) -> Dict[str, int]:
        """Return {product_id: total_stock} for all (or category-filtered) products."""
        with self.db_manager.get_session() as session:
            query = (
                session.query(
                    Product.id,
                    func.coalesce(func.sum(InventoryLevel.quantity), 0).label("total_stock"),
                )
                .outerjoin(InventoryLevel, Product.id == InventoryLevel.product_id)
                .group_by(Product.id)
            )

            if category:
                query = query.filter(Product.category == category)

            return {r.id: int(r.total_stock) for r in query.all()}

    def get_abc_report(
        self,
        days: int = None,
        category: Optional[str] = None,
        a_threshold: float = None,
        b_threshold: float = None,
    ) -> List[Dict[str, Any]]:
        """
        Classify all products by ABC and compute turnover metrics.

        Returns a list of dicts (one per product) sorted by revenue descending.
        Each dict merges ABCItem fields with current stock and turnover data.

        Turnover rate: annualised units sold per unit of stock.
        Days of inventory: how many days current stock will last at current demand.
        """
        days = days or DEFAULT_ANALYTICS_DAYS
        a_thr = a_threshold if a_threshold is not None else ABC_A_THRESHOLD
        b_thr = b_threshold if b_threshold is not None else ABC_B_THRESHOLD

        try:
            products = self._get_product_revenue(days, category)
            stock_map = self._get_stock_map(category)
            items: List[ABCItem] = classify(products, a_thr, b_thr)

            results = []
            for item in items:
                stock = stock_map.get(item.product_id, 0)

                if stock > 0 and item.total_quantity > 0:
                    daily_demand = item.total_quantity / days
                    turnover_rate = round((daily_demand * 365) / stock, 2)
                    days_of_inventory = round(stock / daily_demand, 1)
                else:
                    turnover_rate = 0.0
                    days_of_inventory = None

                results.append({
                    "product_id": item.product_id,
                    "product_name": item.product_name,
                    "category": item.category,
                    "total_revenue": item.total_revenue,
                    "total_quantity": item.total_quantity,
                    "revenue_pct": item.revenue_pct,
                    "cumulative_pct": item.cumulative_pct,
                    "abc_class": item.abc_class,
                    "current_stock": stock,
                    "turnover_rate": turnover_rate,
                    "days_of_inventory": days_of_inventory,
                })

            return results

        except Exception as e:
            self.logger.error(f"ABC report failed: {e}")
            return []

    def get_abc_summary(
        self,
        days: int = None,
        category: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Return per-class summary (A, B, C) derived from the ABC classification.

        Always returns three entries (one per class), even if a class has no products.
        """
        days = days or DEFAULT_ANALYTICS_DAYS

        try:
            products = self._get_product_revenue(days, category)
            items: List[ABCItem] = classify(products, ABC_A_THRESHOLD, ABC_B_THRESHOLD)
            summaries = summarize(items)

            return [
                {
                    "abc_class": s.abc_class,
                    "product_count": s.product_count,
                    "total_revenue": s.total_revenue,
                    "revenue_pct": s.revenue_pct,
                    "product_pct": s.product_pct,
                }
                for s in summaries
            ]

        except Exception as e:
            self.logger.error(f"ABC summary failed: {e}")
            return []

    def get_categories(self) -> List[str]:
        """Return distinct product categories."""
        with self.db_manager.get_session() as session:
            rows = (
                session.query(Product.category)
                .distinct()
                .order_by(Product.category)
                .all()
            )
            return [r.category for r in rows]
