"""
Dashboard View
Main operational dashboard with KPI cards, charts, and low-stock alerts.
"""

import customtkinter as ctk

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.services.inventory_service import InventoryService
from src.services.sales_service import SalesService
from src.services.kpi_service import KPIService
from src.ui.components.kpi_card import KPICard
from src.ui.components.chart_panel import ChartPanel
from src.ui.components.data_table import DataTable
from src.ui.components.filter_bar import FilterBar
from src.ui.theme import (
    COLOR_PRIMARY,
    COLOR_SUCCESS,
    COLOR_WARNING,
    COLOR_DANGER,
    COLOR_NEUTRAL,
    FONT_SUBHEADER,
    FONT_SMALL,
    SECTION_PADDING,
    format_number,
    format_currency,
    format_percentage,
)
from src.i18n import t
from src.logger import LoggerMixin


class DashboardView(ctk.CTkFrame, LoggerMixin):
    """Main operational dashboard."""

    def __init__(self, master, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)

        self._inventory_service = InventoryService()
        self._sales_service = SalesService()
        self._kpi_service = KPIService()

        self._stale = True
        self._build()

    def _build(self):
        """Build the dashboard layout."""
        # Scrollable container
        self._scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self._scroll.pack(fill="both", expand=True)

        # Filter bar
        self._filter_bar = FilterBar(
            self._scroll, on_filter_change=self._apply_filters
        )
        self._filter_bar.pack(
            fill="x", padx=SECTION_PADDING, pady=(SECTION_PADDING, 10)
        )

        # KPI cards row
        self._kpi_frame = ctk.CTkFrame(self._scroll, fg_color="transparent")
        self._kpi_frame.pack(fill="x", padx=SECTION_PADDING, pady=(0, 10))

        self._kpi_cards = {}
        self._kpi_label_keys = {}
        kpi_defs = [
            ("total_skus",      "dash.kpi.total_skus",      COLOR_PRIMARY),
            ("total_units",     "dash.kpi.total_units",     COLOR_PRIMARY),
            ("inventory_value", "dash.kpi.inventory_value", COLOR_SUCCESS),
            ("stockout_rate",   "dash.kpi.stockout_rate",   COLOR_DANGER),
            ("days_of_supply",  "dash.kpi.days_of_supply",  COLOR_WARNING),
            ("carrying_cost",   "dash.kpi.carrying_cost",   COLOR_NEUTRAL),
        ]

        for i, (key, lbl_key, color) in enumerate(kpi_defs):
            card = KPICard(self._kpi_frame, label=t(lbl_key), value="--", color=color)
            card.grid(row=0, column=i, padx=5, pady=5, sticky="nsew")
            self._kpi_cards[key] = card
            self._kpi_label_keys[key] = lbl_key
            self._kpi_frame.grid_columnconfigure(i, weight=1)

        # Charts row
        charts_frame = ctk.CTkFrame(self._scroll, fg_color="transparent")
        charts_frame.pack(fill="x", padx=SECTION_PADDING, pady=(0, 10))
        charts_frame.grid_columnconfigure(0, weight=1)
        charts_frame.grid_columnconfigure(1, weight=1)

        self._category_chart = ChartPanel(charts_frame, figsize=(5, 3))
        self._category_chart.grid(row=0, column=0, padx=(0, 5), pady=5, sticky="nsew")

        self._sales_chart = ChartPanel(charts_frame, figsize=(5, 3))
        self._sales_chart.grid(row=0, column=1, padx=(5, 0), pady=5, sticky="nsew")

        # Low stock alerts
        self._lbl_alerts = ctk.CTkLabel(
            self._scroll, text=t("dash.section.alerts"), font=FONT_SUBHEADER, anchor="w"
        )
        self._lbl_alerts.pack(fill="x", padx=SECTION_PADDING, pady=(5, 3))

        self._alert_table = DataTable(
            self._scroll,
            columns=[
                {"key": "id",          "label": t("col.sku"),          "width": 100},
                {"key": "name",        "label": t("col.product_name"), "width": 250},
                {"key": "category",    "label": t("col.category"),     "width": 120},
                {"key": "total_stock", "label": t("col.stock"),        "width": 80,  "anchor": "center"},
                {"key": "status",      "label": t("col.status"),       "width": 120},
            ],
            height=6,
        )
        self._alert_table.pack(fill="x", padx=SECTION_PADDING, pady=(0, SECTION_PADDING))

    def refresh(self):
        """Refresh all dashboard data."""
        if not self._stale:
            return
        self._stale = False

        try:
            # Populate filter dropdowns
            categories = self._inventory_service.get_categories()
            warehouses = self._inventory_service.get_warehouses()
            self._filter_bar.set_categories(categories)
            self._filter_bar.set_warehouses(warehouses)

            # Load data with current filters
            filters = self._filter_bar.get_filters()
            self._load_data(filters)

        except Exception as e:
            self.logger.error(f"Dashboard refresh failed: {e}")

    def _apply_filters(self, filters: dict):
        """Re-query data with new filters."""
        self._load_data(filters)

    def _load_data(self, filters: dict):
        """Load all dashboard data with the given filters."""
        category = filters.get("category")
        warehouse_id = filters.get("warehouse_id")
        days = filters.get("days", 30)

        try:
            # KPIs
            kpis = self._kpi_service.get_all_kpis(
                category=category, warehouse_id=warehouse_id, days=days
            )
            self._update_kpi_cards(kpis)

            # Charts
            self._update_category_chart(warehouse_id)
            self._update_sales_chart(days, category)

            # Low stock alerts
            low_stock = self._inventory_service.get_low_stock_items(
                threshold=10, category=category
            )
            self._alert_table.load_data(low_stock)

        except Exception as e:
            self.logger.error(f"Dashboard data load failed: {e}")

    def _update_kpi_cards(self, kpis: dict):
        """Update KPI card values."""
        sh = kpis.get("stock_health", {})
        sl = kpis.get("service_level", {})
        fi = kpis.get("financial", {})

        self._kpi_cards["total_skus"].update(
            format_number(sh.get("total_products", 0))
        )
        self._kpi_cards["total_units"].update(
            format_number(sh.get("total_units", 0))
        )
        self._kpi_cards["inventory_value"].update(
            format_currency(fi.get("total_inventory_value", 0)),
            color=COLOR_SUCCESS,
        )

        stockout_rate = sl.get("stockout_rate", 0)
        stockout_color = COLOR_DANGER if stockout_rate > 5 else (
            COLOR_WARNING if stockout_rate > 0 else COLOR_SUCCESS
        )
        self._kpi_cards["stockout_rate"].update(
            format_percentage(stockout_rate),
            trend=f"{sl.get('stockout_count', 0)} products",
            color=stockout_color,
        )

        dos = sh.get("days_of_supply")
        dos_text = f"{dos:.0f} days" if dos and dos != float("inf") else "N/A"
        dos_color = COLOR_DANGER if dos and dos < 7 else (
            COLOR_WARNING if dos and dos < 14 else COLOR_SUCCESS
        )
        self._kpi_cards["days_of_supply"].update(dos_text, color=dos_color)

        self._kpi_cards["carrying_cost"].update(
            format_currency(fi.get("carrying_cost_monthly", 0)),
            trend="per month",
        )

    def _update_category_chart(self, warehouse_id=None):
        """Update the stock-by-category bar chart."""
        try:
            data = self._inventory_service.get_stock_by_category(warehouse_id)
            labels = [d["category"] for d in data[:8]]
            values = [d["total_value"] for d in data[:8]]
            self._category_chart.plot_bar(
                labels, values, title=t("dash.chart.category")
            )
        except Exception as e:
            self.logger.error(f"Category chart error: {e}")

    def _update_sales_chart(self, days=30, category=None):
        """Update the daily sales trend line chart."""
        try:
            data = self._sales_service.get_daily_sales_summary(days, category)
            dates = [d["date"][-5:] for d in data]  # MM-DD format
            revenues = [d["total_revenue"] for d in data]
            self._sales_chart.plot_line(
                dates, revenues, title=t("dash.chart.sales"), ylabel="Revenue ($)"
            )
        except Exception as e:
            self.logger.error(f"Sales chart error: {e}")

    def mark_stale(self):
        """Mark view for refresh on next display."""
        self._stale = True

    def update_language(self):
        """Refresh all translatable text after a language change."""
        self._lbl_alerts.configure(text=t("dash.section.alerts"))
        for key, lbl_key in self._kpi_label_keys.items():
            self._kpi_cards[key].set_label(t(lbl_key))
        _update_tree_headings(self._alert_table, {
            "id":          "col.sku",
            "name":        "col.product_name",
            "category":    "col.category",
            "total_stock": "col.stock",
            "status":      "col.status",
        })
        self.mark_stale()


def _update_tree_headings(table, col_key_map: dict) -> None:
    from src.i18n import t as _t
    for col_key, trans_key in col_key_map.items():
        try:
            table._tree.heading(col_key, text=_t(trans_key))
        except Exception:
            pass
