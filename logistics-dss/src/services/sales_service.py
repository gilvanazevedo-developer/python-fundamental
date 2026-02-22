"""
Sales Service
Query and aggregate sales data for KPIs and charts.
"""

from typing import Dict, Any, List, Optional
from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import func

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from config.constants import DEFAULT_LOOKBACK_DAYS
from src.database.connection import get_db_manager
from src.database.models import Product, SalesRecord
from src.logger import LoggerMixin


class SalesService(LoggerMixin):
    """Provides sales query and aggregation methods."""

    def __init__(self, db_manager=None):
        self.db_manager = db_manager or get_db_manager()

    def _lookback_date(self, days: int = None) -> date:
        """Calculate the start date for a lookback period."""
        days = days or DEFAULT_LOOKBACK_DAYS
        return date.today() - timedelta(days=days)

    def get_sales_by_period(
        self,
        start: date,
        end: date,
        category: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Get sales records within a date range."""
        with self.db_manager.get_session() as session:
            query = (
                session.query(SalesRecord)
                .filter(SalesRecord.date >= start, SalesRecord.date <= end)
            )

            if category:
                query = query.join(Product).filter(Product.category == category)

            rows = query.order_by(SalesRecord.date.desc()).all()

            return [
                {
                    "id": r.id,
                    "date": str(r.date),
                    "product_id": r.product_id,
                    "warehouse_id": r.warehouse_id,
                    "quantity_sold": int(r.quantity_sold),
                    "revenue": float(r.revenue),
                }
                for r in rows
            ]

    def get_daily_sales_summary(
        self,
        days: int = None,
        category: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Get daily sales totals for the last N days."""
        start = self._lookback_date(days)

        with self.db_manager.get_session() as session:
            query = (
                session.query(
                    SalesRecord.date,
                    func.sum(SalesRecord.quantity_sold).label("total_quantity"),
                    func.sum(SalesRecord.revenue).label("total_revenue"),
                    func.count(SalesRecord.id).label("transaction_count"),
                )
                .filter(SalesRecord.date >= start)
                .group_by(SalesRecord.date)
            )

            if category:
                query = query.join(Product).filter(Product.category == category)

            rows = query.order_by(SalesRecord.date.asc()).all()

            return [
                {
                    "date": str(r.date),
                    "total_quantity": int(r.total_quantity),
                    "total_revenue": float(r.total_revenue),
                    "transaction_count": int(r.transaction_count),
                }
                for r in rows
            ]

    def get_sales_by_category(
        self, days: int = None
    ) -> List[Dict[str, Any]]:
        """Get revenue aggregated by product category."""
        start = self._lookback_date(days)

        with self.db_manager.get_session() as session:
            rows = (
                session.query(
                    Product.category,
                    func.sum(SalesRecord.revenue).label("total_revenue"),
                    func.sum(SalesRecord.quantity_sold).label("total_quantity"),
                )
                .join(Product, SalesRecord.product_id == Product.id)
                .filter(SalesRecord.date >= start)
                .group_by(Product.category)
                .order_by(func.sum(SalesRecord.revenue).desc())
                .all()
            )

            return [
                {
                    "category": r.category,
                    "total_revenue": float(r.total_revenue),
                    "total_quantity": int(r.total_quantity),
                }
                for r in rows
            ]

    def get_top_products(
        self, n: int = 10, days: int = None
    ) -> List[Dict[str, Any]]:
        """Get top N products by revenue."""
        start = self._lookback_date(days)

        with self.db_manager.get_session() as session:
            rows = (
                session.query(
                    Product.id,
                    Product.name,
                    Product.category,
                    func.sum(SalesRecord.revenue).label("total_revenue"),
                    func.sum(SalesRecord.quantity_sold).label("total_quantity"),
                )
                .join(Product, SalesRecord.product_id == Product.id)
                .filter(SalesRecord.date >= start)
                .group_by(Product.id)
                .order_by(func.sum(SalesRecord.revenue).desc())
                .limit(n)
                .all()
            )

            return [
                {
                    "id": r.id,
                    "name": r.name,
                    "category": r.category,
                    "total_revenue": float(r.total_revenue),
                    "total_quantity": int(r.total_quantity),
                }
                for r in rows
            ]

    def get_total_revenue(
        self, days: int = None, category: Optional[str] = None
    ) -> float:
        """Get total revenue for the last N days."""
        start = self._lookback_date(days)

        with self.db_manager.get_session() as session:
            query = (
                session.query(func.coalesce(func.sum(SalesRecord.revenue), 0))
                .filter(SalesRecord.date >= start)
            )

            if category:
                query = query.join(Product).filter(Product.category == category)

            return float(query.scalar() or 0)

    def get_total_quantity_sold(
        self, days: int = None, category: Optional[str] = None
    ) -> int:
        """Get total units sold for the last N days."""
        start = self._lookback_date(days)

        with self.db_manager.get_session() as session:
            query = (
                session.query(func.coalesce(func.sum(SalesRecord.quantity_sold), 0))
                .filter(SalesRecord.date >= start)
            )

            if category:
                query = query.join(Product).filter(Product.category == category)

            return int(query.scalar() or 0)

    def get_average_daily_demand(
        self, product_id: str, days: int = None
    ) -> float:
        """Get mean daily quantity sold for a product."""
        start = self._lookback_date(days)

        with self.db_manager.get_session() as session:
            result = (
                session.query(
                    func.sum(SalesRecord.quantity_sold).label("total_sold"),
                    func.count(func.distinct(SalesRecord.date)).label("days_with_sales"),
                )
                .filter(
                    SalesRecord.product_id == product_id,
                    SalesRecord.date >= start,
                )
                .one()
            )

            if not result.total_sold or not result.days_with_sales:
                return 0.0

            days_in_period = days or DEFAULT_LOOKBACK_DAYS
            return float(result.total_sold) / days_in_period

    def get_sales_day_count(self, days: int = None) -> int:
        """Get the number of distinct days with sales in the period."""
        start = self._lookback_date(days)

        with self.db_manager.get_session() as session:
            return (
                session.query(func.count(func.distinct(SalesRecord.date)))
                .filter(SalesRecord.date >= start)
                .scalar()
            ) or 0
