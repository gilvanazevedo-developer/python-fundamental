"""
Optimization Service
Pulls inventory, sales, and cost data from the DB, then runs EOQ optimization
for every product, returning actionable reorder policies and cost savings.
"""

import math
import statistics
from typing import Dict, Any, List, Optional
from datetime import date, timedelta

from sqlalchemy import func

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.database.connection import get_db_manager
from src.database.models import Product, InventoryLevel, SalesRecord
from src.analytics.optimization import optimize, OptimizationResult
from src.logger import LoggerMixin
from config.constants import (
    CARRYING_COST_RATE,
    DEFAULT_ANALYTICS_DAYS,
    DEFAULT_LEAD_TIME_DAYS,
    DEFAULT_ORDERING_COST,
    SERVICE_LEVEL_Z,
)


class OptimizationService(LoggerMixin):
    """Computes EOQ-based inventory optimization for all products."""

    def __init__(self, db_manager=None):
        self.db_manager = db_manager or get_db_manager()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _lookback_date(self, days: int) -> date:
        return date.today() - timedelta(days=days)

    def _get_product_demand_stats(
        self, days: int, category: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Return per-product demand stats: daily avg, std-dev, and current stock.
        Only products with at least one sale are included.
        """
        start = self._lookback_date(days)

        with self.db_manager.get_session() as session:
            # Per-day demand per product
            daily_rows = (
                session.query(
                    SalesRecord.product_id,
                    SalesRecord.date,
                    func.sum(SalesRecord.quantity_sold).label("daily_qty"),
                )
                .filter(SalesRecord.date >= start)
                .group_by(SalesRecord.product_id, SalesRecord.date)
                .all()
            )

        # Aggregate std-dev per product in Python (SQLite lacks stddev)
        from collections import defaultdict
        daily_by_product: Dict[str, List[int]] = defaultdict(list)
        for row in daily_rows:
            daily_by_product[row.product_id].append(int(row.daily_qty))

        # Fill missing days with zero so std-dev reflects demand uncertainty
        for pid in daily_by_product:
            recorded = len(daily_by_product[pid])
            zeros_to_add = max(0, days - recorded)
            daily_by_product[pid].extend([0] * zeros_to_add)

        with self.db_manager.get_session() as session:
            # Products + cost + stock
            query = (
                session.query(
                    Product.id,
                    Product.name,
                    Product.category,
                    Product.unit_cost,
                    func.coalesce(func.sum(InventoryLevel.quantity), 0).label("total_stock"),
                    func.coalesce(func.sum(SalesRecord.quantity_sold), 0).label("total_sold"),
                )
                .outerjoin(InventoryLevel, Product.id == InventoryLevel.product_id)
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

        results = []
        for r in rows:
            pid = r.id
            total_sold = int(r.total_sold)
            if total_sold == 0:
                continue  # skip products with no sales

            daily_series = daily_by_product.get(pid, [])
            avg_daily = total_sold / days
            std_dev = statistics.pstdev(daily_series) if len(daily_series) >= 2 else 0.0

            results.append({
                "product_id": pid,
                "product_name": r.name,
                "category": r.category,
                "unit_cost": float(r.unit_cost) if r.unit_cost else 0.0,
                "avg_daily_demand": avg_daily,
                "std_dev_daily": std_dev,
                "current_stock": int(r.total_stock),
            })

        return results

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_optimization_report(
        self,
        category: Optional[str] = None,
        days: int = None,
        ordering_cost: float = None,
        service_level_z: float = None,
        lead_time_days: int = None,
    ) -> List[Dict[str, Any]]:
        """
        Compute EOQ optimization for all products with sales history.

        Returns a list of dicts (one per product) sorted by
        potential_savings descending — highest opportunity first.

        Each dict contains all OptimizationResult fields plus a human-
        readable ``recommendation`` text.
        """
        days = days or DEFAULT_ANALYTICS_DAYS
        ordering_cost = ordering_cost if ordering_cost is not None else DEFAULT_ORDERING_COST
        z = service_level_z if service_level_z is not None else SERVICE_LEVEL_Z
        lead_time = lead_time_days or DEFAULT_LEAD_TIME_DAYS

        try:
            stats = self._get_product_demand_stats(days, category)
            results = []

            for s in stats:
                result: Optional[OptimizationResult] = optimize(
                    product_id=s["product_id"],
                    product_name=s["product_name"],
                    category=s["category"],
                    daily_demand=s["avg_daily_demand"],
                    std_dev_daily=s["std_dev_daily"],
                    unit_cost=s["unit_cost"],
                    carrying_cost_rate=CARRYING_COST_RATE,
                    ordering_cost=ordering_cost,
                    lead_time_days=lead_time,
                    current_stock=s["current_stock"],
                    service_level_z=z,
                )
                if result is None:
                    continue

                # Build a recommendation text
                if s["current_stock"] < result.reorder_point:
                    rec = "ORDER NOW — stock below reorder point"
                elif result.potential_savings > 50:
                    if result.current_order_qty > result.eoq * 1.5:
                        rec = f"Reduce order qty to {result.eoq:.0f} units (currently over-ordering)"
                    else:
                        rec = f"Increase order freq; optimal qty is {result.eoq:.0f} units"
                else:
                    rec = "Policy near-optimal"

                results.append({
                    "product_id": result.product_id,
                    "product_name": result.product_name,
                    "category": result.category,
                    "annual_demand": result.annual_demand,
                    "eoq": result.eoq,
                    "safety_stock": result.safety_stock,
                    "reorder_point": result.reorder_point,
                    "orders_per_year": result.orders_per_year,
                    "eoq_total_cost": result.eoq_total_cost,
                    "current_order_qty": result.current_order_qty,
                    "current_total_cost": result.current_total_cost,
                    "potential_savings": result.potential_savings,
                    "savings_pct": result.savings_pct,
                    "current_stock": s["current_stock"],
                    "recommendation": rec,
                })

            results.sort(key=lambda r: r["potential_savings"], reverse=True)
            return results

        except Exception as e:
            self.logger.error(f"Optimization report failed: {e}")
            return []

    def get_optimization_summary(
        self,
        category: Optional[str] = None,
        days: int = None,
        ordering_cost: float = None,
        service_level_z: float = None,
    ) -> Dict[str, Any]:
        """
        Aggregate financial summary across all optimizable products.

        Returns:
            total_current_cost    — sum of current annual inventory costs
            total_optimal_cost    — sum of EOQ-optimal annual costs
            total_savings         — total_current − total_optimal
            savings_pct           — total_savings / total_current × 100
            products_with_savings — count of SKUs where savings > 0
            total_products        — count of SKUs in the report
        """
        report = self.get_optimization_report(
            category=category, days=days,
            ordering_cost=ordering_cost, service_level_z=service_level_z,
        )

        if not report:
            return {
                "total_current_cost": 0.0,
                "total_optimal_cost": 0.0,
                "total_savings": 0.0,
                "savings_pct": 0.0,
                "products_with_savings": 0,
                "total_products": 0,
            }

        total_current = sum(r["current_total_cost"] for r in report)
        total_optimal = sum(r["eoq_total_cost"] for r in report)
        total_savings = max(0.0, total_current - total_optimal)
        savings_pct = (total_savings / total_current * 100) if total_current > 0 else 0.0
        with_savings = sum(1 for r in report if r["potential_savings"] > 0)

        return {
            "total_current_cost": round(total_current, 2),
            "total_optimal_cost": round(total_optimal, 2),
            "total_savings": round(total_savings, 2),
            "savings_pct": round(savings_pct, 1),
            "products_with_savings": with_savings,
            "total_products": len(report),
        }

    def get_savings_by_category(
        self,
        days: int = None,
        ordering_cost: float = None,
    ) -> List[Dict[str, Any]]:
        """
        Return potential savings aggregated by product category.
        Sorted by savings descending (largest opportunity first).
        """
        report = self.get_optimization_report(days=days, ordering_cost=ordering_cost)

        from collections import defaultdict
        by_cat: Dict[str, Dict] = defaultdict(
            lambda: {"savings": 0.0, "current_cost": 0.0, "product_count": 0}
        )
        for r in report:
            cat = r["category"]
            by_cat[cat]["savings"] += r["potential_savings"]
            by_cat[cat]["current_cost"] += r["current_total_cost"]
            by_cat[cat]["product_count"] += 1

        result = [
            {
                "category": cat,
                "potential_savings": round(v["savings"], 2),
                "current_cost": round(v["current_cost"], 2),
                "product_count": v["product_count"],
            }
            for cat, v in by_cat.items()
        ]
        result.sort(key=lambda x: x["potential_savings"], reverse=True)
        return result

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
