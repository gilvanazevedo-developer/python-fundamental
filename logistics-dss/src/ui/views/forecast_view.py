"""
Forecast View
Demand forecasting dashboard: reorder recommendations table with
per-product historical + projected demand chart.
"""

import customtkinter as ctk

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.services.forecast_service import ForecastService
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
    FONT_BODY,
    FONT_SMALL,
    SECTION_PADDING,
    format_number,
    format_currency,
)
from src.logger import LoggerMixin

_URGENCY_COLORS = {
    "CRITICAL": COLOR_DANGER,
    "WARNING": COLOR_WARNING,
    "OK": COLOR_SUCCESS,
    "NO DEMAND": COLOR_NEUTRAL,
}

_METHODS = ["SMA", "WMA", "LINEAR"]
_PERIODS = ["30", "60", "90", "180"]
_HORIZONS = ["7", "14", "30", "60"]


class ForecastView(ctk.CTkFrame, LoggerMixin):
    """Demand Forecasting and Reorder Recommendation view."""

    def __init__(self, master, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)

        self._forecast_service = ForecastService()
        self._stale = True
        self._selected_product_id: str | None = None
        self._build()

    # ------------------------------------------------------------------
    # Layout
    # ------------------------------------------------------------------

    def _build(self):
        self._scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self._scroll.pack(fill="both", expand=True)

        # ── Top controls ───────────────────────────────────────────────
        controls = ctk.CTkFrame(self._scroll, fg_color="transparent")
        controls.pack(fill="x", padx=SECTION_PADDING, pady=(SECTION_PADDING, 6))

        # Category filter
        ctk.CTkLabel(controls, text="Category:", font=FONT_SMALL).grid(
            row=0, column=0, padx=(0, 4), sticky="w"
        )
        self._cat_var = ctk.StringVar(value="All")
        self._cat_menu = ctk.CTkOptionMenu(
            controls, variable=self._cat_var,
            values=["All"], width=140, height=28,
            command=self._on_controls_changed,
        )
        self._cat_menu.grid(row=0, column=1, padx=(0, 16), sticky="w")

        # Lookback period
        ctk.CTkLabel(controls, text="History (days):", font=FONT_SMALL).grid(
            row=0, column=2, padx=(0, 4), sticky="w"
        )
        self._period_var = ctk.StringVar(value="90")
        self._period_menu = ctk.CTkOptionMenu(
            controls, variable=self._period_var,
            values=_PERIODS, width=90, height=28,
            command=self._on_controls_changed,
        )
        self._period_menu.grid(row=0, column=3, padx=(0, 16), sticky="w")

        # Forecast horizon
        ctk.CTkLabel(controls, text="Horizon (days):", font=FONT_SMALL).grid(
            row=0, column=4, padx=(0, 4), sticky="w"
        )
        self._horizon_var = ctk.StringVar(value="30")
        self._horizon_menu = ctk.CTkOptionMenu(
            controls, variable=self._horizon_var,
            values=_HORIZONS, width=90, height=28,
            command=self._on_controls_changed,
        )
        self._horizon_menu.grid(row=0, column=5, padx=(0, 16), sticky="w")

        # Forecast method
        ctk.CTkLabel(controls, text="Method:", font=FONT_SMALL).grid(
            row=0, column=6, padx=(0, 4), sticky="w"
        )
        self._method_var = ctk.StringVar(value="SMA")
        self._method_menu = ctk.CTkOptionMenu(
            controls, variable=self._method_var,
            values=_METHODS, width=100, height=28,
            command=self._on_controls_changed,
        )
        self._method_menu.grid(row=0, column=7, padx=(0, 16), sticky="w")

        # Refresh button
        ctk.CTkButton(
            controls, text="Refresh", width=90, height=28,
            command=self._reload,
        ).grid(row=0, column=8, sticky="w")

        # ── Summary KPI cards ──────────────────────────────────────────
        ctk.CTkLabel(
            self._scroll, text="Demand Overview", font=FONT_SUBHEADER, anchor="w"
        ).pack(fill="x", padx=SECTION_PADDING, pady=(10, 3))

        kpi_frame = ctk.CTkFrame(self._scroll, fg_color="transparent")
        kpi_frame.pack(fill="x", padx=SECTION_PADDING, pady=(0, 10))

        kpi_defs = [
            ("critical",  "Critical SKUs",  COLOR_DANGER),
            ("warning",   "Warning SKUs",   COLOR_WARNING),
            ("ok",        "On-Track SKUs",  COLOR_SUCCESS),
            ("no_demand", "No-Demand SKUs", COLOR_NEUTRAL),
        ]
        self._kpi_cards: dict[str, KPICard] = {}
        for col, (key, label, color) in enumerate(kpi_defs):
            card = KPICard(kpi_frame, label=label, value="--", color=color)
            card.grid(row=0, column=col, padx=5, pady=5, sticky="nsew")
            kpi_frame.grid_columnconfigure(col, weight=1)
            self._kpi_cards[key] = card

        # ── Forecast chart (appears after row selection) ───────────────
        ctk.CTkLabel(
            self._scroll, text="Product Demand Forecast", font=FONT_SUBHEADER, anchor="w"
        ).pack(fill="x", padx=SECTION_PADDING, pady=(5, 3))

        self._chart_hint = ctk.CTkLabel(
            self._scroll,
            text="Select a product row below to view its forecast chart.",
            font=FONT_SMALL, text_color=COLOR_NEUTRAL, anchor="w",
        )
        self._chart_hint.pack(fill="x", padx=SECTION_PADDING)

        self._forecast_chart = ChartPanel(self._scroll, figsize=(12, 3))
        self._forecast_chart.pack(
            fill="x", padx=SECTION_PADDING, pady=(0, 10)
        )

        # ── Reorder recommendations table ──────────────────────────────
        ctk.CTkLabel(
            self._scroll, text="Reorder Recommendations", font=FONT_SUBHEADER, anchor="w"
        ).pack(fill="x", padx=SECTION_PADDING, pady=(5, 3))

        self._reco_table = DataTable(
            self._scroll,
            columns=[
                {"key": "urgency",            "label": "Urgency",     "width": 90,  "anchor": "center"},
                {"key": "product_id",         "label": "SKU",         "width": 100},
                {"key": "product_name",       "label": "Product",     "width": 200},
                {"key": "category",           "label": "Category",    "width": 110},
                {"key": "current_stock",      "label": "Stock",       "width": 75,  "anchor": "e"},
                {"key": "avg_daily_demand",   "label": "Avg/Day",     "width": 75,  "anchor": "e"},
                {"key": "forecast_daily",     "label": "Fcst/Day",    "width": 75,  "anchor": "e"},
                {"key": "reorder_point",      "label": "ROP",         "width": 65,  "anchor": "e"},
                {"key": "safety_stock",       "label": "Safety Stk",  "width": 80,  "anchor": "e"},
                {"key": "days_until_stockout","label": "Days Left",   "width": 80,  "anchor": "e"},
            ],
            on_select=self._on_row_selected,
            height=14,
        )
        self._reco_table.pack(
            fill="both", padx=SECTION_PADDING, pady=(0, SECTION_PADDING), expand=True
        )

    # ------------------------------------------------------------------
    # Refresh / filter lifecycle
    # ------------------------------------------------------------------

    def refresh(self):
        if not self._stale:
            return
        self._stale = False
        try:
            cats = self._forecast_service.get_categories()
            self._cat_menu.configure(values=["All"] + cats)
        except Exception as e:
            self.logger.error(f"Forecast category load failed: {e}")
        self._reload()

    def _on_controls_changed(self, _value=None):
        self._reload()

    def _reload(self):
        """Reload the reorder recommendations with current control settings."""
        category = self._cat_var.get()
        if category == "All":
            category = None
        days = int(self._period_var.get())
        horizon = int(self._horizon_var.get())
        method = self._method_var.get()

        try:
            recommendations = self._forecast_service.get_reorder_recommendations(
                category=category, days=days,
                horizon_days=horizon, method=method,
            )
            self._update_kpi_cards(recommendations)
            self._load_table(recommendations)
            self._selected_product_id = None
            self._forecast_chart.clear()
            self._chart_hint.configure(
                text="Select a product row below to view its forecast chart."
            )
        except Exception as e:
            self.logger.error(f"Forecast reload failed: {e}")

    # ------------------------------------------------------------------
    # Data update helpers
    # ------------------------------------------------------------------

    def _update_kpi_cards(self, recommendations: list):
        from collections import Counter
        counts = Counter(r["urgency"] for r in recommendations)
        self._kpi_cards["critical"].update(
            str(counts.get("CRITICAL", 0)), color=COLOR_DANGER
        )
        self._kpi_cards["warning"].update(
            str(counts.get("WARNING", 0)), color=COLOR_WARNING
        )
        self._kpi_cards["ok"].update(
            str(counts.get("OK", 0)), color=COLOR_SUCCESS
        )
        self._kpi_cards["no_demand"].update(
            str(counts.get("NO DEMAND", 0)), color=COLOR_NEUTRAL
        )

    def _load_table(self, recommendations: list):
        """Format and load rows into the recommendations table."""
        display_rows = []
        for r in recommendations:
            doi = r.get("days_until_stockout")
            display_rows.append({
                **r,
                "avg_daily_demand": f"{r['avg_daily_demand']:.1f}",
                "forecast_daily": f"{r['forecast_daily']:.1f}",
                "days_until_stockout": f"{doi:.0f}" if doi is not None else "—",
            })
        self._reco_table.load_data(display_rows)

    def _on_row_selected(self, row: dict):
        """When user clicks a row, load that product's forecast chart."""
        product_id = row.get("product_id")
        if not product_id or product_id == self._selected_product_id:
            return
        self._selected_product_id = product_id
        self._chart_hint.configure(text="")
        self._draw_forecast_chart(product_id)

    def _draw_forecast_chart(self, product_id: str):
        """Fetch and render the historical + forecast chart for a product."""
        days = int(self._period_var.get())
        horizon = int(self._horizon_var.get())
        method = self._method_var.get()

        try:
            data = self._forecast_service.get_product_forecast(
                product_id, days=days, horizon_days=horizon, method=method
            )
            if not data:
                self._forecast_chart.clear()
                return

            hist_dates = data["historical_dates"]
            hist_qty = data["historical_quantities"]
            fcst_dates = data["forecast_dates"]
            fcst_vals = data["forecast_values"]

            # Build combined x-axis labels (show every N-th for readability)
            all_dates = hist_dates + fcst_dates
            all_qty_hist = list(hist_qty) + [None] * len(fcst_dates)
            all_qty_fcst = [None] * len(hist_dates) + list(fcst_vals)

            step = max(1, len(all_dates) // 12)
            x_labels = [d[-5:] if i % step == 0 else "" for i, d in enumerate(all_dates)]

            ax = self._forecast_chart._ax
            ax.clear()

            x = list(range(len(all_dates)))

            # Historical bars
            hist_x = x[: len(hist_dates)]
            ax.bar(hist_x, hist_qty, color=COLOR_PRIMARY, alpha=0.7,
                   label="Historical", zorder=3)

            # Forecast line
            fcst_x = x[len(hist_dates):]
            ax.plot(fcst_x, fcst_vals, color=COLOR_DANGER, linewidth=2,
                    linestyle="--", marker="o", markersize=3,
                    label=f"{method} Forecast", zorder=4)

            # Vertical divider between history and forecast
            if hist_x:
                ax.axvline(x=hist_x[-1] + 0.5, color=COLOR_NEUTRAL,
                           linestyle=":", linewidth=1)

            ax.set_xticks(range(len(all_dates)))
            ax.set_xticklabels(x_labels, rotation=45, ha="right", fontsize=8)
            ax.legend(fontsize=9, loc="upper left")

            title = (
                f"{data['product_name']} — {method} | "
                f"Forecast: {data['forecast_daily']:.1f} units/day | "
                f"MAE: {data['mae']:.1f}"
            )
            self._forecast_chart._style_axis(title)
            self._forecast_chart._figure.tight_layout()
            self._forecast_chart._mpl_canvas.draw_idle()

        except Exception as e:
            self.logger.error(f"Forecast chart error for {product_id}: {e}")

    def mark_stale(self):
        self._stale = True
