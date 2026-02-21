"""
Analytics View
ABC classification dashboard with class summary cards, charts, and detail table.
"""

import customtkinter as ctk

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.services.analytics_service import AnalyticsService
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
    SECTION_PADDING,
    format_currency,
    format_percentage,
    format_number,
)
from src.logger import LoggerMixin

# Colour scheme for ABC classes
_CLASS_COLORS = {"A": COLOR_SUCCESS, "B": COLOR_WARNING, "C": COLOR_NEUTRAL}


class AnalyticsView(ctk.CTkFrame, LoggerMixin):
    """ABC classification and inventory-turnover analytics view."""

    def __init__(self, master, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)

        self._analytics_service = AnalyticsService()
        self._stale = True
        self._build()

    # ------------------------------------------------------------------
    # Layout
    # ------------------------------------------------------------------

    def _build(self):
        """Build the analytics layout."""
        self._scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self._scroll.pack(fill="both", expand=True)

        # Filter bar (category + period; no warehouse for ABC)
        self._filter_bar = FilterBar(
            self._scroll,
            on_filter_change=self._apply_filters,
            show_period=True,
        )
        self._filter_bar.pack(
            fill="x", padx=SECTION_PADDING, pady=(SECTION_PADDING, 10)
        )

        # Section title
        ctk.CTkLabel(
            self._scroll,
            text="ABC Classification — Class Summary",
            font=FONT_SUBHEADER,
            anchor="w",
        ).pack(fill="x", padx=SECTION_PADDING, pady=(5, 3))

        # Three summary cards (A, B, C) in one row
        cards_frame = ctk.CTkFrame(self._scroll, fg_color="transparent")
        cards_frame.pack(fill="x", padx=SECTION_PADDING, pady=(0, 10))

        self._class_cards: dict[str, dict] = {}
        class_defs = [
            ("A", "Class A — High Value", COLOR_SUCCESS),
            ("B", "Class B — Medium Value", COLOR_WARNING),
            ("C", "Class C — Low Value", COLOR_NEUTRAL),
        ]

        for col, (cls, label, color) in enumerate(class_defs):
            frame = ctk.CTkFrame(cards_frame)
            frame.grid(row=0, column=col, padx=5, pady=5, sticky="nsew")
            cards_frame.grid_columnconfigure(col, weight=1)

            # Class header label
            ctk.CTkLabel(frame, text=label, font=FONT_SUBHEADER,
                         text_color=color, anchor="w").pack(
                fill="x", padx=12, pady=(10, 4)
            )

            count_card = KPICard(frame, label="Products", value="--", color=color)
            count_card.pack(fill="x", padx=8, pady=3)

            rev_card = KPICard(frame, label="Revenue", value="--", color=color)
            rev_card.pack(fill="x", padx=8, pady=3)

            pct_card = KPICard(frame, label="Revenue Share", value="--", color=color)
            pct_card.pack(fill="x", padx=8, pady=(3, 10))

            self._class_cards[cls] = {
                "count": count_card,
                "revenue": rev_card,
                "pct": pct_card,
            }

        # Charts row
        charts_frame = ctk.CTkFrame(self._scroll, fg_color="transparent")
        charts_frame.pack(fill="x", padx=SECTION_PADDING, pady=(0, 10))
        charts_frame.grid_columnconfigure(0, weight=1)
        charts_frame.grid_columnconfigure(1, weight=1)

        self._revenue_chart = ChartPanel(charts_frame, figsize=(5, 3))
        self._revenue_chart.grid(row=0, column=0, padx=(0, 5), pady=5, sticky="nsew")

        self._product_chart = ChartPanel(charts_frame, figsize=(5, 3))
        self._product_chart.grid(row=0, column=1, padx=(5, 0), pady=5, sticky="nsew")

        # Detail table
        ctk.CTkLabel(
            self._scroll,
            text="Product Classification Detail",
            font=FONT_SUBHEADER,
            anchor="w",
        ).pack(fill="x", padx=SECTION_PADDING, pady=(5, 3))

        self._detail_table = DataTable(
            self._scroll,
            columns=[
                {"key": "abc_class",       "label": "Class",       "width": 60,  "anchor": "center"},
                {"key": "product_id",      "label": "SKU",         "width": 100},
                {"key": "product_name",    "label": "Product",     "width": 220},
                {"key": "category",        "label": "Category",    "width": 110},
                {"key": "total_revenue",   "label": "Revenue ($)", "width": 110, "anchor": "e"},
                {"key": "revenue_pct",     "label": "Rev %",       "width": 70,  "anchor": "e"},
                {"key": "cumulative_pct",  "label": "Cumul %",     "width": 75,  "anchor": "e"},
                {"key": "current_stock",   "label": "Stock",       "width": 75,  "anchor": "e"},
                {"key": "turnover_rate",   "label": "Turnover",    "width": 80,  "anchor": "e"},
                {"key": "days_of_inventory", "label": "DOI",       "width": 65,  "anchor": "e"},
            ],
            height=16,
        )
        self._detail_table.pack(
            fill="both", padx=SECTION_PADDING, pady=(0, SECTION_PADDING), expand=True
        )

    # ------------------------------------------------------------------
    # Refresh / filter
    # ------------------------------------------------------------------

    def refresh(self):
        """Refresh all analytics data if stale."""
        if not self._stale:
            return
        self._stale = False

        try:
            categories = self._analytics_service.get_categories()
            self._filter_bar.set_categories(categories)

            filters = self._filter_bar.get_filters()
            self._load_data(filters)

        except Exception as e:
            self.logger.error(f"Analytics refresh failed: {e}")

    def _apply_filters(self, filters: dict):
        """Re-query data when the user changes a filter."""
        self._load_data(filters)

    def _load_data(self, filters: dict):
        """Load ABC summary and detail with the given filters."""
        category = filters.get("category")
        days = filters.get("days", 90)

        try:
            summaries = self._analytics_service.get_abc_summary(
                days=days, category=category
            )
            self._update_class_cards(summaries)
            self._update_revenue_chart(summaries)
            self._update_product_chart(summaries)

            report = self._analytics_service.get_abc_report(
                days=days, category=category
            )
            self._load_detail_table(report)

        except Exception as e:
            self.logger.error(f"Analytics data load failed: {e}")

    # ------------------------------------------------------------------
    # Update helpers
    # ------------------------------------------------------------------

    def _update_class_cards(self, summaries: list):
        """Populate the three ABC class summary cards."""
        for s in summaries:
            cls = s["abc_class"]
            cards = self._class_cards.get(cls)
            if not cards:
                continue
            color = _CLASS_COLORS.get(cls, COLOR_NEUTRAL)
            cards["count"].update(format_number(s["product_count"]), color=color)
            cards["revenue"].update(format_currency(s["total_revenue"]), color=color)
            cards["pct"].update(
                format_percentage(s["revenue_pct"]),
                trend=f"{s['product_pct']:.1f}% of SKUs",
                color=color,
            )

    def _update_revenue_chart(self, summaries: list):
        """Bar chart: revenue by ABC class."""
        try:
            labels = [s["abc_class"] for s in summaries]
            values = [s["total_revenue"] for s in summaries]
            colors = [_CLASS_COLORS.get(lbl, COLOR_NEUTRAL) for lbl in labels]
            # ChartPanel.plot_bar takes a single color; draw manually for multi-color
            self._revenue_chart._ax.clear()
            if any(v > 0 for v in values):
                bars = self._revenue_chart._ax.bar(
                    labels, values, color=colors, width=0.5, zorder=3
                )
                self._revenue_chart._style_axis("Revenue by ABC Class ($)")
            else:
                self._revenue_chart.plot_bar([], [], title="Revenue by ABC Class ($)")
                return
            self._revenue_chart._figure.tight_layout()
            self._revenue_chart._mpl_canvas.draw_idle()
        except Exception as e:
            self.logger.error(f"Revenue chart error: {e}")

    def _update_product_chart(self, summaries: list):
        """Bar chart: product count by ABC class."""
        try:
            labels = [s["abc_class"] for s in summaries]
            values = [s["product_count"] for s in summaries]
            colors = [_CLASS_COLORS.get(lbl, COLOR_NEUTRAL) for lbl in labels]
            self._product_chart._ax.clear()
            if any(v > 0 for v in values):
                self._product_chart._ax.bar(
                    labels, values, color=colors, width=0.5, zorder=3
                )
                self._product_chart._style_axis("Products per ABC Class")
            else:
                self._product_chart.plot_bar([], [], title="Products per ABC Class")
                return
            self._product_chart._figure.tight_layout()
            self._product_chart._mpl_canvas.draw_idle()
        except Exception as e:
            self.logger.error(f"Product chart error: {e}")

    def _load_detail_table(self, report: list):
        """Load the product-level ABC report into the detail table."""
        # Format display values
        display_rows = []
        for row in report:
            doi = row.get("days_of_inventory")
            display_rows.append({
                **row,
                "total_revenue": f"{row['total_revenue']:,.2f}",
                "revenue_pct": f"{row['revenue_pct']:.2f}%",
                "cumulative_pct": f"{row['cumulative_pct']:.2f}%",
                "turnover_rate": f"{row['turnover_rate']:.2f}x",
                "days_of_inventory": f"{doi:.0f}" if doi is not None else "—",
            })
        self._detail_table.load_data(display_rows)

    def mark_stale(self):
        """Mark the view for refresh on next display."""
        self._stale = True
