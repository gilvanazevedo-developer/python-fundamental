"""
Report Service
Consolidates data from all modules into an executive report,
and exports to Excel (multi-sheet) or CSV files.
"""

import csv
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional

import pandas as pd

import sys
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.database.connection import get_db_manager
from src.services.inventory_service import InventoryService
from src.services.sales_service import SalesService
from src.services.kpi_service import KPIService
from src.services.analytics_service import AnalyticsService
from src.services.forecast_service import ForecastService
from src.services.optimization_service import OptimizationService
from src.logger import LoggerMixin
from config.constants import DEFAULT_ANALYTICS_DAYS


class ReportService(LoggerMixin):
    """
    Aggregates data from all analytical services and exports reports.

    All sub-services share the same db_manager to avoid redundant connections.
    """

    def __init__(self, db_manager=None):
        self.db_manager = db_manager or get_db_manager()
        self._inventory = InventoryService(self.db_manager)
        self._sales = SalesService(self.db_manager)
        self._kpi = KPIService(self.db_manager)
        self._analytics = AnalyticsService(self.db_manager)
        self._forecast = ForecastService(self.db_manager)
        self._optimization = OptimizationService(self.db_manager)

    # ------------------------------------------------------------------
    # Executive report assembly
    # ------------------------------------------------------------------

    def get_executive_report(self, days: int = None) -> Dict[str, Any]:
        """
        Build a consolidated executive report covering all modules.

        Returns a dict with sections:
            period_days         — analysis window
            generated_at        — ISO timestamp
            financial_summary   — revenue + inventory cost KPIs
            stock_health        — stock levels + days of supply
            service_level       — stockout rate + fill rate
            abc_summary         — A/B/C class breakdown (3 rows)
            top_products        — top 10 SKUs by revenue
            sales_trend         — daily revenue for the period
            reorder_alerts      — CRITICAL + WARNING SKUs
            optimization_summary— aggregate EOQ savings potential
            top_savings_skus    — top 10 SKUs by potential savings
            stock_by_category   — stock value per category
        """
        days = days or DEFAULT_ANALYTICS_DAYS

        try:
            report: Dict[str, Any] = {
                "period_days": days,
                "generated_at": datetime.now().isoformat(timespec="seconds"),
            }

            # Financial & stock KPIs
            kpis = self._kpi.get_all_kpis(days=days)
            report["financial_summary"] = kpis.get("financial", {})
            report["stock_health"] = kpis.get("stock_health", {})
            report["service_level"] = kpis.get("service_level", {})

            # ABC class distribution
            report["abc_summary"] = self._analytics.get_abc_summary(days=days)

            # Top products by revenue
            report["top_products"] = self._sales.get_top_products(n=10, days=days)

            # Daily sales trend
            report["sales_trend"] = self._sales.get_daily_sales_summary(days=days)

            # Reorder alerts (CRITICAL + WARNING only)
            all_recos = self._forecast.get_reorder_recommendations(days=days)
            report["reorder_alerts"] = [
                r for r in all_recos
                if r.get("urgency") in ("CRITICAL", "WARNING")
            ]

            # Optimization summary + top savings SKUs
            report["optimization_summary"] = self._optimization.get_optimization_summary(
                days=days
            )
            opt_report = self._optimization.get_optimization_report(days=days)
            report["top_savings_skus"] = opt_report[:10]

            # Stock by category
            report["stock_by_category"] = self._inventory.get_stock_by_category()

            return report

        except Exception as e:
            self.logger.error(f"Executive report assembly failed: {e}")
            return {"period_days": days, "generated_at": datetime.now().isoformat(),
                    "error": str(e)}

    # ------------------------------------------------------------------
    # Excel export
    # ------------------------------------------------------------------

    def export_to_excel(self, report: Dict[str, Any], filepath: str) -> bool:
        """
        Write the executive report to a multi-sheet Excel workbook.

        Sheets created:
            Summary          — top-level KPI table
            ABC Analysis     — class A/B/C breakdown
            Top Products     — top-10 revenue SKUs
            Sales Trend      — daily revenue series
            Reorder Alerts   — CRITICAL + WARNING items
            Optimization     — top-10 EOQ savings opportunities

        Returns True on success, False on failure.
        """
        try:
            with pd.ExcelWriter(filepath, engine="openpyxl") as writer:

                # ── Sheet 1: Summary ───────────────────────────────────
                fin = report.get("financial_summary", {})
                health = report.get("stock_health", {})
                svc = report.get("service_level", {})
                opt = report.get("optimization_summary", {})

                summary_rows = [
                    ("Report period (days)",         report.get("period_days")),
                    ("Generated at",                 report.get("generated_at")),
                    ("",                             ""),
                    ("── Inventory ──",               ""),
                    ("Total SKUs",                   health.get("total_products")),
                    ("Total units in stock",         health.get("total_units")),
                    ("Inventory value ($)",          fin.get("total_inventory_value")),
                    ("Carrying cost / month ($)",    fin.get("carrying_cost_monthly")),
                    ("Days of supply",               health.get("days_of_supply")),
                    ("Inventory turnover (ann.)",    health.get("inventory_turnover")),
                    ("",                             ""),
                    ("── Service Level ──",           ""),
                    ("Stockout rate (%)",            svc.get("stockout_rate")),
                    ("Fill rate (%)",                svc.get("fill_rate")),
                    ("Stockout count",               svc.get("stockout_count")),
                    ("Low stock count",              svc.get("low_stock_count")),
                    ("",                             ""),
                    ("── Revenue ──",                 ""),
                    (f"Revenue last {report.get('period_days')} days ($)",
                     fin.get("revenue_period")),
                    ("",                             ""),
                    ("── Optimisation ──",            ""),
                    ("Current annual inventory cost ($)", opt.get("total_current_cost")),
                    ("Optimal annual inventory cost ($)", opt.get("total_optimal_cost")),
                    ("Potential savings ($)",        opt.get("total_savings")),
                    ("Savings opportunity (%)",      opt.get("savings_pct")),
                    ("SKUs with savings",            opt.get("products_with_savings")),
                ]
                pd.DataFrame(summary_rows, columns=["Metric", "Value"]).to_excel(
                    writer, sheet_name="Summary", index=False
                )

                # ── Sheet 2: ABC Analysis ──────────────────────────────
                abc = report.get("abc_summary", [])
                if abc:
                    pd.DataFrame(abc).to_excel(
                        writer, sheet_name="ABC Analysis", index=False
                    )

                # ── Sheet 3: Top Products ──────────────────────────────
                top = report.get("top_products", [])
                if top:
                    pd.DataFrame(top).to_excel(
                        writer, sheet_name="Top Products", index=False
                    )

                # ── Sheet 4: Sales Trend ───────────────────────────────
                trend = report.get("sales_trend", [])
                if trend:
                    pd.DataFrame(trend).to_excel(
                        writer, sheet_name="Sales Trend", index=False
                    )

                # ── Sheet 5: Reorder Alerts ────────────────────────────
                alerts = report.get("reorder_alerts", [])
                if alerts:
                    # Drop large nested fields before export
                    pd.DataFrame(alerts).to_excel(
                        writer, sheet_name="Reorder Alerts", index=False
                    )
                else:
                    pd.DataFrame([{"message": "No critical or warning items"}]).to_excel(
                        writer, sheet_name="Reorder Alerts", index=False
                    )

                # ── Sheet 6: Optimization ──────────────────────────────
                opt_rows = report.get("top_savings_skus", [])
                if opt_rows:
                    pd.DataFrame(opt_rows).to_excel(
                        writer, sheet_name="Optimization", index=False
                    )

            self.logger.info(f"Excel report exported to {filepath}")
            return True

        except Exception as e:
            self.logger.error(f"Excel export failed: {e}")
            return False

    # ------------------------------------------------------------------
    # CSV export
    # ------------------------------------------------------------------

    def export_to_csv(self, report: Dict[str, Any], folder: str) -> bool:
        """
        Write the executive report as a set of CSV files in ``folder``.

        Files created (skipped if no data):
            executive_summary.csv
            abc_analysis.csv
            top_products.csv
            sales_trend.csv
            reorder_alerts.csv
            optimization.csv

        Returns True on success, False on failure.
        """
        try:
            folder_path = Path(folder)
            folder_path.mkdir(parents=True, exist_ok=True)

            def _write(filename: str, rows: List[dict]):
                if not rows:
                    return
                filepath = folder_path / filename
                keys = list(rows[0].keys())
                with open(filepath, "w", newline="", encoding="utf-8") as f:
                    writer = csv.DictWriter(f, fieldnames=keys)
                    writer.writeheader()
                    writer.writerows(rows)

            # Summary as flat key/value pairs
            fin = report.get("financial_summary", {})
            health = report.get("stock_health", {})
            svc = report.get("service_level", {})
            opt = report.get("optimization_summary", {})
            summary_rows = [
                {"metric": k, "value": v}
                for section in (fin, health, svc, opt)
                for k, v in section.items()
            ]
            _write("executive_summary.csv", summary_rows)
            _write("abc_analysis.csv",    report.get("abc_summary", []))
            _write("top_products.csv",    report.get("top_products", []))
            _write("sales_trend.csv",     report.get("sales_trend", []))
            _write("reorder_alerts.csv",  report.get("reorder_alerts", []))
            _write("optimization.csv",    report.get("top_savings_skus", []))

            self.logger.info(f"CSV reports exported to {folder}")
            return True

        except Exception as e:
            self.logger.error(f"CSV export failed: {e}")
            return False
