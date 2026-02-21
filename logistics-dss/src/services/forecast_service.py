"""
Forecast Service
Pulls historical daily demand from the DB, runs the forecasting engine,
and computes reorder recommendations for each product.
"""

import math
from typing import Dict, Any, List, Optional
from datetime import date, timedelta

from sqlalchemy import func

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.database.connection import get_db_manager
from src.database.models import Product, InventoryLevel, SalesRecord
from src.analytics.forecasting import (
    build_series,
    forecast as compute_forecast,
    ForecastResult,
)
from src.logger import LoggerMixin
from config.constants import (
    DEFAULT_ANALYTICS_DAYS,
    DEFAULT_FORECAST_HORIZON_DAYS,
    DEFAULT_LEAD_TIME_DAYS,
    SAFETY_STOCK_FACTOR,
    FORECAST_SMA_WINDOW,
)


class ForecastService(LoggerMixin):
    """Provides demand forecasting and reorder recommendation services."""

    def __init__(self, db_manager=None):
        self.db_manager = db_manager or get_db_manager()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _lookback_date(self, days: int) -> date:
        return date.today() - timedelta(days=days)

    def _get_daily_demand_rows(
        self, product_id: str, days: int
    ) -> List[Dict[str, Any]]:
        """Return per-day sales totals for a single product."""
        start = self._lookback_date(days)

        with self.db_manager.get_session() as session:
            rows = (
                session.query(
                    SalesRecord.date.label("date"),
                    func.sum(SalesRecord.quantity_sold).label("total_quantity"),
                )
                .filter(
                    SalesRecord.product_id == product_id,
                    SalesRecord.date >= start,
                )
                .group_by(SalesRecord.date)
                .order_by(SalesRecord.date.asc())
                .all()
            )
            return [
                {"date": str(r.date), "total_quantity": int(r.total_quantity)}
                for r in rows
            ]

    def _get_all_products_with_stock(
        self, category: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Return products with their current total stock."""
        with self.db_manager.get_session() as session:
            query = (
                session.query(
                    Product.id,
                    Product.name,
                    Product.category,
                    Product.unit_cost,
                    func.coalesce(func.sum(InventoryLevel.quantity), 0).label("total_stock"),
                )
                .outerjoin(InventoryLevel, Product.id == InventoryLevel.product_id)
                .group_by(Product.id)
            )
            if category:
                query = query.filter(Product.category == category)

            return [
                {
                    "product_id": r.id,
                    "product_name": r.name,
                    "category": r.category,
                    "unit_cost": float(r.unit_cost) if r.unit_cost else 0.0,
                    "total_stock": int(r.total_stock),
                }
                for r in query.all()
            ]

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_product_forecast(
        self,
        product_id: str,
        days: int = None,
        horizon_days: int = None,
        method: str = "SMA",
        window: int = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Compute a demand forecast for a single product.

        Returns a dict with all ForecastResult fields plus the full
        historical series (dates + quantities) for charting.
        Returns None if the product has no sales history.
        """
        days = days or DEFAULT_ANALYTICS_DAYS
        horizon_days = horizon_days or DEFAULT_FORECAST_HORIZON_DAYS
        window = window or FORECAST_SMA_WINDOW

        try:
            # Fetch product info
            with self.db_manager.get_session() as session:
                product = session.query(Product).filter(Product.id == product_id).first()
                if not product:
                    return None
                p_name = product.name
                p_cat = product.category

            # Build daily demand series
            start = self._lookback_date(days)
            end = date.today() - timedelta(days=1)   # up to yesterday
            raw = self._get_daily_demand_rows(product_id, days)

            series = build_series(product_id, p_name, p_cat, raw, start, end)

            # Compute forecast
            result: ForecastResult = compute_forecast(
                series, method=method, horizon_days=horizon_days, window=window
            )

            return {
                "product_id": result.product_id,
                "product_name": result.product_name,
                "category": result.category,
                "method": result.method,
                "horizon_days": result.horizon_days,
                "historical_daily_avg": result.historical_daily_avg,
                "forecast_daily": result.forecast_daily,
                "forecast_total": result.forecast_total,
                "std_dev": result.std_dev,
                "mae": result.mae,
                # Historical series for the chart
                "historical_dates": series.dates,
                "historical_quantities": series.quantities,
                # Forecast series for the chart
                "forecast_dates": result.forecast_dates,
                "forecast_values": result.forecast_values,
            }

        except Exception as e:
            self.logger.error(f"Forecast failed for {product_id}: {e}")
            return None

    def get_reorder_recommendations(
        self,
        category: Optional[str] = None,
        days: int = None,
        horizon_days: int = None,
        method: str = "SMA",
        lead_time_days: int = None,
    ) -> List[Dict[str, Any]]:
        """
        Compute reorder recommendations for all products.

        For each product:
          - Forecast daily demand using the requested method
          - Compute safety stock = SAFETY_STOCK_FACTOR × std_dev × √lead_time
          - Compute reorder point (ROP) = forecast_daily × lead_time + safety_stock
          - Compute days until stockout = current_stock / forecast_daily
          - Urgency: CRITICAL (≤ lead_time), WARNING (≤ 2× lead_time), OK

        Returns list sorted by days_until_stockout ascending (most urgent first).
        """
        days = days or DEFAULT_ANALYTICS_DAYS
        horizon_days = horizon_days or DEFAULT_FORECAST_HORIZON_DAYS
        lead_time = lead_time_days or DEFAULT_LEAD_TIME_DAYS

        try:
            products = self._get_all_products_with_stock(category)
            start = self._lookback_date(days)
            end = date.today() - timedelta(days=1)

            recommendations = []

            for p in products:
                pid = p["product_id"]
                raw = self._get_daily_demand_rows(pid, days)
                series = build_series(
                    pid, p["product_name"], p["category"], raw, start, end
                )

                result: ForecastResult = compute_forecast(
                    series, method=method, horizon_days=horizon_days,
                    window=FORECAST_SMA_WINDOW
                )

                stock = p["total_stock"]
                daily_fcst = result.forecast_daily
                std_dev = result.std_dev

                # Safety stock (clipped at 0)
                safety_stock = max(0.0, SAFETY_STOCK_FACTOR * std_dev * math.sqrt(lead_time))

                # Reorder point
                rop = round(daily_fcst * lead_time + safety_stock)

                # Days until stockout
                if daily_fcst > 0:
                    days_until_stockout = round(stock / daily_fcst, 1)
                else:
                    days_until_stockout = None   # no demand → no stockout

                # Urgency
                if daily_fcst <= 0:
                    urgency = "NO DEMAND"
                elif days_until_stockout is not None and days_until_stockout <= lead_time:
                    urgency = "CRITICAL"
                elif days_until_stockout is not None and days_until_stockout <= lead_time * 2:
                    urgency = "WARNING"
                else:
                    urgency = "OK"

                recommendations.append({
                    "product_id": pid,
                    "product_name": p["product_name"],
                    "category": p["category"],
                    "current_stock": stock,
                    "avg_daily_demand": result.historical_daily_avg,
                    "forecast_daily": daily_fcst,
                    "forecast_total": result.forecast_total,
                    "std_dev": std_dev,
                    "safety_stock": round(safety_stock),
                    "reorder_point": rop,
                    "days_until_stockout": days_until_stockout,
                    "urgency": urgency,
                    "lead_time_days": lead_time,
                    "mae": result.mae,
                })

            # Sort: CRITICAL first, then WARNING, then OK/NO DEMAND
            urgency_rank = {"CRITICAL": 0, "WARNING": 1, "OK": 2, "NO DEMAND": 3}
            recommendations.sort(
                key=lambda r: (
                    urgency_rank.get(r["urgency"], 9),
                    r["days_until_stockout"] if r["days_until_stockout"] is not None else 9999,
                )
            )

            return recommendations

        except Exception as e:
            self.logger.error(f"Reorder recommendations failed: {e}")
            return []

    def get_products(self, category: Optional[str] = None) -> List[Dict[str, Any]]:
        """Return all products (optionally filtered) for populating selectors."""
        return self._get_all_products_with_stock(category)

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
