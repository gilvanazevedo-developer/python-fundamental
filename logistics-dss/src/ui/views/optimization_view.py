"""
Optimization View
EOQ-based inventory optimization dashboard:
  - Financial summary KPIs (current cost vs optimal cost, total savings)
  - Savings-by-category bar chart
  - Per-product optimization detail table
"""

import customtkinter as ctk

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.services.optimization_service import OptimizationService
from src.ui.components.kpi_card import KPICard
from src.ui.components.chart_panel import ChartPanel
from src.ui.components.data_table import DataTable
from src.ui.theme import (
    COLOR_PRIMARY,
    COLOR_SUCCESS,
    COLOR_WARNING,
    COLOR_DANGER,
    COLOR_NEUTRAL,
    FONT_SUBHEADER,
    FONT_SMALL,
    SECTION_PADDING,
    format_currency,
    format_percentage,
    format_number,
)
from src.logger import LoggerMixin
from config.constants import SERVICE_LEVELS, DEFAULT_ORDERING_COST

_PERIODS = ["30", "60", "90", "180"]


class OptimizationView(ctk.CTkFrame, LoggerMixin):
    """EOQ Inventory Optimization view."""

    def __init__(self, master, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)

        self._optimization_service = OptimizationService()
        self._stale = True
        self._build()

    # ------------------------------------------------------------------
    # Layout
    # ------------------------------------------------------------------

    def _build(self):
        self._scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self._scroll.pack(fill="both", expand=True)

        # ── Controls ───────────────────────────────────────────────────
        controls = ctk.CTkFrame(self._scroll, fg_color="transparent")
        controls.pack(fill="x", padx=SECTION_PADDING, pady=(SECTION_PADDING, 6))

        col = 0

        ctk.CTkLabel(controls, text="Category:", font=FONT_SMALL).grid(
            row=0, column=col, padx=(0, 4), sticky="w"
        )
        col += 1
        self._cat_var = ctk.StringVar(value="All")
        self._cat_menu = ctk.CTkOptionMenu(
            controls, variable=self._cat_var, values=["All"],
            width=140, height=28, command=self._on_change,
        )
        self._cat_menu.grid(row=0, column=col, padx=(0, 14), sticky="w")
        col += 1

        ctk.CTkLabel(controls, text="History (days):", font=FONT_SMALL).grid(
            row=0, column=col, padx=(0, 4), sticky="w"
        )
        col += 1
        self._period_var = ctk.StringVar(value="90")
        ctk.CTkOptionMenu(
            controls, variable=self._period_var, values=_PERIODS,
            width=90, height=28, command=self._on_change,
        ).grid(row=0, column=col, padx=(0, 14), sticky="w")
        col += 1

        ctk.CTkLabel(controls, text="Ordering cost ($):", font=FONT_SMALL).grid(
            row=0, column=col, padx=(0, 4), sticky="w"
        )
        col += 1
        self._ordering_cost_var = ctk.StringVar(value=str(int(DEFAULT_ORDERING_COST)))
        self._ordering_cost_entry = ctk.CTkEntry(
            controls, textvariable=self._ordering_cost_var, width=70, height=28,
        )
        self._ordering_cost_entry.grid(row=0, column=col, padx=(0, 14), sticky="w")
        col += 1

        ctk.CTkLabel(controls, text="Service level:", font=FONT_SMALL).grid(
            row=0, column=col, padx=(0, 4), sticky="w"
        )
        col += 1
        self._svc_var = ctk.StringVar(value="95% (Z=1.65)")
        ctk.CTkOptionMenu(
            controls, variable=self._svc_var,
            values=list(SERVICE_LEVELS.keys()),
            width=130, height=28, command=self._on_change,
        ).grid(row=0, column=col, padx=(0, 14), sticky="w")
        col += 1

        ctk.CTkButton(
            controls, text="Refresh", width=90, height=28,
            command=self._reload,
        ).grid(row=0, column=col, sticky="w")

        # ── Summary KPI cards ──────────────────────────────────────────
        ctk.CTkLabel(
            self._scroll, text="Cost Optimisation Summary",
            font=FONT_SUBHEADER, anchor="w",
        ).pack(fill="x", padx=SECTION_PADDING, pady=(10, 3))

        kpi_frame = ctk.CTkFrame(self._scroll, fg_color="transparent")
        kpi_frame.pack(fill="x", padx=SECTION_PADDING, pady=(0, 10))

        kpi_defs = [
            ("current_cost",  "Current Annual Cost",    COLOR_DANGER),
            ("optimal_cost",  "Optimal Annual Cost",    COLOR_SUCCESS),
            ("savings",       "Potential Savings",      COLOR_WARNING),
            ("skus_optimized","SKUs w/ Savings",        COLOR_PRIMARY),
        ]
        self._kpi_cards: dict[str, KPICard] = {}
        for i, (key, label, color) in enumerate(kpi_defs):
            card = KPICard(kpi_frame, label=label, value="--", color=color)
            card.grid(row=0, column=i, padx=5, pady=5, sticky="nsew")
            kpi_frame.grid_columnconfigure(i, weight=1)
            self._kpi_cards[key] = card

        # ── Charts row ─────────────────────────────────────────────────
        charts_frame = ctk.CTkFrame(self._scroll, fg_color="transparent")
        charts_frame.pack(fill="x", padx=SECTION_PADDING, pady=(0, 10))
        charts_frame.grid_columnconfigure(0, weight=2)
        charts_frame.grid_columnconfigure(1, weight=1)

        self._savings_chart = ChartPanel(charts_frame, figsize=(6, 3))
        self._savings_chart.grid(row=0, column=0, padx=(0, 5), pady=5, sticky="nsew")

        self._cost_chart = ChartPanel(charts_frame, figsize=(4, 3))
        self._cost_chart.grid(row=0, column=1, padx=(5, 0), pady=5, sticky="nsew")

        # ── Detail table ───────────────────────────────────────────────
        ctk.CTkLabel(
            self._scroll, text="Per-Product Optimisation Detail",
            font=FONT_SUBHEADER, anchor="w",
        ).pack(fill="x", padx=SECTION_PADDING, pady=(5, 3))

        self._detail_table = DataTable(
            self._scroll,
            columns=[
                {"key": "product_id",       "label": "SKU",          "width": 100},
                {"key": "product_name",     "label": "Product",      "width": 200},
                {"key": "category",         "label": "Category",     "width": 110},
                {"key": "current_stock",    "label": "Stock",        "width": 70,  "anchor": "e"},
                {"key": "eoq",              "label": "EOQ",          "width": 70,  "anchor": "e"},
                {"key": "reorder_point",    "label": "ROP",          "width": 70,  "anchor": "e"},
                {"key": "safety_stock",     "label": "Safety Stk",   "width": 80,  "anchor": "e"},
                {"key": "orders_per_year",  "label": "Orders/Yr",    "width": 80,  "anchor": "e"},
                {"key": "eoq_total_cost",   "label": "Opt Cost ($)", "width": 100, "anchor": "e"},
                {"key": "current_total_cost","label": "Curr Cost ($)","width": 100, "anchor": "e"},
                {"key": "potential_savings","label": "Savings ($)",  "width": 95,  "anchor": "e"},
                {"key": "savings_pct",      "label": "Sav %",        "width": 65,  "anchor": "e"},
                {"key": "recommendation",   "label": "Recommendation","width": 260},
            ],
            height=14,
        )
        self._detail_table.pack(
            fill="both", padx=SECTION_PADDING, pady=(0, SECTION_PADDING), expand=True
        )

    # ------------------------------------------------------------------
    # Refresh / control lifecycle
    # ------------------------------------------------------------------

    def refresh(self):
        if not self._stale:
            return
        self._stale = False
        try:
            cats = self._optimization_service.get_categories()
            self._cat_menu.configure(values=["All"] + cats)
        except Exception as e:
            self.logger.error(f"Optimisation category load failed: {e}")
        self._reload()

    def _on_change(self, _value=None):
        self._reload()

    def _reload(self):
        category = self._cat_var.get()
        if category == "All":
            category = None
        days = int(self._period_var.get())
        z = SERVICE_LEVELS.get(self._svc_var.get(), 1.65)

        try:
            ordering_cost = float(self._ordering_cost_var.get())
        except ValueError:
            ordering_cost = DEFAULT_ORDERING_COST

        try:
            summary = self._optimization_service.get_optimization_summary(
                category=category, days=days,
                ordering_cost=ordering_cost, service_level_z=z,
            )
            self._update_kpi_cards(summary)

            by_cat = self._optimization_service.get_savings_by_category(
                days=days, ordering_cost=ordering_cost,
            )
            self._update_savings_chart(by_cat)
            self._update_cost_chart(summary)

            report = self._optimization_service.get_optimization_report(
                category=category, days=days,
                ordering_cost=ordering_cost, service_level_z=z,
            )
            self._load_table(report)

        except Exception as e:
            self.logger.error(f"Optimisation reload failed: {e}")

    # ------------------------------------------------------------------
    # Update helpers
    # ------------------------------------------------------------------

    def _update_kpi_cards(self, summary: dict):
        savings = summary.get("total_savings", 0)
        savings_pct = summary.get("savings_pct", 0)
        with_savings = summary.get("products_with_savings", 0)
        total = summary.get("total_products", 0)

        self._kpi_cards["current_cost"].update(
            format_currency(summary.get("total_current_cost", 0)), color=COLOR_DANGER
        )
        self._kpi_cards["optimal_cost"].update(
            format_currency(summary.get("total_optimal_cost", 0)), color=COLOR_SUCCESS
        )
        self._kpi_cards["savings"].update(
            format_currency(savings),
            trend=f"{savings_pct:.1f}% reduction",
            color=COLOR_WARNING if savings > 0 else COLOR_NEUTRAL,
        )
        self._kpi_cards["skus_optimized"].update(
            format_number(with_savings),
            trend=f"of {total} optimisable SKUs",
            color=COLOR_PRIMARY,
        )

    def _update_savings_chart(self, by_cat: list):
        """Horizontal bar chart: potential savings by category."""
        try:
            labels = [r["category"] for r in by_cat[:10]]
            values = [r["potential_savings"] for r in by_cat[:10]]
            self._savings_chart.plot_horizontal_bar(
                labels, values, title="Potential Savings by Category ($)",
                color=COLOR_WARNING,
            )
        except Exception as e:
            self.logger.error(f"Savings chart error: {e}")

    def _update_cost_chart(self, summary: dict):
        """Bar chart: current vs optimal total annual cost."""
        try:
            labels = ["Current Cost", "Optimal Cost"]
            values = [
                summary.get("total_current_cost", 0),
                summary.get("total_optimal_cost", 0),
            ]
            colors = [COLOR_DANGER, COLOR_SUCCESS]
            ax = self._cost_chart._ax
            ax.clear()
            if any(v > 0 for v in values):
                ax.bar(labels, values, color=colors, width=0.5, zorder=3)
                self._cost_chart._style_axis("Annual Inventory Cost ($)")
                self._cost_chart._figure.tight_layout()
                self._cost_chart._mpl_canvas.draw_idle()
            else:
                self._cost_chart.plot_bar([], [], title="Annual Inventory Cost ($)")
        except Exception as e:
            self.logger.error(f"Cost chart error: {e}")

    def _load_table(self, report: list):
        display_rows = []
        for r in report:
            display_rows.append({
                **r,
                "eoq":               f"{r['eoq']:.0f}",
                "reorder_point":     f"{r['reorder_point']:.0f}",
                "safety_stock":      f"{r['safety_stock']:.0f}",
                "orders_per_year":   f"{r['orders_per_year']:.1f}",
                "eoq_total_cost":    f"{r['eoq_total_cost']:,.0f}",
                "current_total_cost":f"{r['current_total_cost']:,.0f}",
                "potential_savings": f"{r['potential_savings']:,.0f}",
                "savings_pct":       f"{r['savings_pct']:.1f}%",
            })
        self._detail_table.load_data(display_rows)

    def mark_stale(self):
        self._stale = True
