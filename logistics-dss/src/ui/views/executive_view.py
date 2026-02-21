"""
Executive View
Management cockpit: consolidated KPIs from all analytical modules,
trend charts, and one-click Excel / CSV export.
"""

import tkinter as tk
from tkinter import filedialog, messagebox
import customtkinter as ctk

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.services.report_service import ReportService
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
from src.i18n import t
from src.logger import LoggerMixin

_PERIODS = ["30", "60", "90", "180"]


class ExecutiveView(ctk.CTkFrame, LoggerMixin):
    """Management executive dashboard with consolidated KPIs and export."""

    def __init__(self, master, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)

        self._report_service = ReportService()
        self._stale = True
        self._report_data: dict = {}
        self._build()

    # ------------------------------------------------------------------
    # Layout
    # ------------------------------------------------------------------

    def _build(self):
        self._scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self._scroll.pack(fill="both", expand=True)

        # ── Header + controls ──────────────────────────────────────────
        header = ctk.CTkFrame(self._scroll, fg_color="transparent")
        header.pack(fill="x", padx=SECTION_PADDING, pady=(SECTION_PADDING, 6))

        self._lbl_title = ctk.CTkLabel(
            header, text=t("exec.title"), font=FONT_SUBHEADER, anchor="w"
        )
        self._lbl_title.pack(side="left")

        btn_frame = ctk.CTkFrame(header, fg_color="transparent")
        btn_frame.pack(side="right")

        self._lbl_period = ctk.CTkLabel(btn_frame, text=t("common.period"), font=FONT_SMALL)
        self._lbl_period.pack(side="left", padx=(0, 4))

        self._period_var = ctk.StringVar(value="90")
        ctk.CTkOptionMenu(
            btn_frame, variable=self._period_var, values=_PERIODS,
            width=80, height=28, command=self._on_period_change,
        ).pack(side="left", padx=(0, 12))

        self._btn_excel = ctk.CTkButton(
            btn_frame, text=t("common.export_excel"), width=110, height=28,
            fg_color=COLOR_SUCCESS, hover_color="#25895e",
            command=self._export_excel,
        )
        self._btn_excel.pack(side="left", padx=(0, 6))

        self._btn_csv = ctk.CTkButton(
            btn_frame, text=t("common.export_csv"), width=95, height=28,
            fg_color=COLOR_PRIMARY,
            command=self._export_csv,
        )
        self._btn_csv.pack(side="left")

        # ── KPI cards row ──────────────────────────────────────────────
        kpi_frame = ctk.CTkFrame(self._scroll, fg_color="transparent")
        kpi_frame.pack(fill="x", padx=SECTION_PADDING, pady=(8, 10))

        kpi_defs = [
            ("revenue",         "exec.kpi.revenue",         COLOR_PRIMARY),
            ("inventory_value", "exec.kpi.inventory_value", COLOR_SUCCESS),
            ("carrying_cost",   "exec.kpi.carrying_cost",   COLOR_WARNING),
            ("stockout_rate",   "exec.kpi.stockout_rate",   COLOR_DANGER),
            ("savings",         "exec.kpi.savings",         COLOR_WARNING),
            ("fill_rate",       "exec.kpi.fill_rate",       COLOR_SUCCESS),
        ]
        self._kpi_cards: dict[str, KPICard] = {}
        self._kpi_label_keys: dict[str, str] = {}
        for i, (key, lbl_key, color) in enumerate(kpi_defs):
            card = KPICard(kpi_frame, label=t(lbl_key), value="--", color=color)
            card.grid(row=0, column=i, padx=5, pady=5, sticky="nsew")
            kpi_frame.grid_columnconfigure(i, weight=1)
            self._kpi_cards[key] = card
            self._kpi_label_keys[key] = lbl_key

        # ── Charts row ─────────────────────────────────────────────────
        charts_frame = ctk.CTkFrame(self._scroll, fg_color="transparent")
        charts_frame.pack(fill="x", padx=SECTION_PADDING, pady=(0, 10))
        charts_frame.grid_columnconfigure(0, weight=2)
        charts_frame.grid_columnconfigure(1, weight=1)

        self._trend_chart = ChartPanel(charts_frame, figsize=(7, 3))
        self._trend_chart.grid(row=0, column=0, padx=(0, 5), pady=5, sticky="nsew")

        self._abc_chart = ChartPanel(charts_frame, figsize=(4, 3))
        self._abc_chart.grid(row=0, column=1, padx=(5, 0), pady=5, sticky="nsew")

        # ── Alert tables row ───────────────────────────────────────────
        tables_frame = ctk.CTkFrame(self._scroll, fg_color="transparent")
        tables_frame.pack(fill="x", padx=SECTION_PADDING, pady=(0, 10))
        tables_frame.grid_columnconfigure(0, weight=1)
        tables_frame.grid_columnconfigure(1, weight=1)

        # Reorder Alerts (left)
        self._lbl_alerts = ctk.CTkLabel(
            tables_frame, text=t("exec.section.alerts"),
            font=FONT_SUBHEADER, anchor="w",
        )
        self._lbl_alerts.grid(row=0, column=0, padx=(0, 10), pady=(0, 3), sticky="w")

        self._alert_table = DataTable(
            tables_frame,
            columns=[
                {"key": "urgency",            "label": t("col.status"),    "width": 80,  "anchor": "center"},
                {"key": "product_id",         "label": t("col.sku"),       "width": 90},
                {"key": "product_name",       "label": t("col.product"),   "width": 160},
                {"key": "current_stock",      "label": t("col.stock"),     "width": 60,  "anchor": "e"},
                {"key": "days_until_stockout","label": t("col.days_left"), "width": 70,  "anchor": "e"},
                {"key": "reorder_point",      "label": t("col.rop"),       "width": 55,  "anchor": "e"},
            ],
            height=7,
        )
        self._alert_table.grid(row=1, column=0, padx=(0, 10), sticky="nsew")

        # Top Savings (right)
        self._lbl_savings = ctk.CTkLabel(
            tables_frame, text=t("exec.section.savings"),
            font=FONT_SUBHEADER, anchor="w",
        )
        self._lbl_savings.grid(row=0, column=1, padx=(10, 0), pady=(0, 3), sticky="w")

        self._savings_table = DataTable(
            tables_frame,
            columns=[
                {"key": "product_id",        "label": t("col.sku"),            "width": 90},
                {"key": "product_name",      "label": t("col.product"),        "width": 160},
                {"key": "eoq",               "label": t("col.eoq"),            "width": 60,  "anchor": "e"},
                {"key": "potential_savings", "label": t("col.savings_dollar"), "width": 90,  "anchor": "e"},
                {"key": "savings_pct",       "label": t("col.savings_pct"),    "width": 55,  "anchor": "e"},
            ],
            height=7,
        )
        self._savings_table.grid(row=1, column=1, padx=(10, 0), sticky="nsew")

        # ── Top products table ─────────────────────────────────────────
        self._lbl_top_products = ctk.CTkLabel(
            self._scroll, text=t("exec.section.top_products"),
            font=FONT_SUBHEADER, anchor="w",
        )
        self._lbl_top_products.pack(fill="x", padx=SECTION_PADDING, pady=(5, 3))

        self._products_table = DataTable(
            self._scroll,
            columns=[
                {"key": "id",             "label": t("col.sku"),            "width": 100},
                {"key": "name",           "label": t("col.product"),        "width": 220},
                {"key": "category",       "label": t("col.category"),       "width": 110},
                {"key": "total_revenue",  "label": t("col.revenue_dollar"), "width": 120, "anchor": "e"},
                {"key": "total_quantity", "label": t("col.units_sold"),     "width": 90,  "anchor": "e"},
            ],
            height=7,
        )
        self._products_table.pack(
            fill="x", padx=SECTION_PADDING, pady=(0, SECTION_PADDING)
        )

    # ------------------------------------------------------------------
    # Refresh / period
    # ------------------------------------------------------------------

    def refresh(self):
        if not self._stale:
            return
        self._stale = False
        self._reload()

    def _on_period_change(self, _value=None):
        self._stale = True
        self._reload()

    def _reload(self):
        days = int(self._period_var.get())
        self._kpi_cards["revenue"].configure()

        try:
            self._report_data = self._report_service.get_executive_report(days=days)
            self._update_kpi_cards()
            self._update_trend_chart()
            self._update_abc_chart()
            self._load_alert_table()
            self._load_savings_table()
            self._load_products_table()
        except Exception as e:
            self.logger.error(f"Executive dashboard reload failed: {e}")

    # ------------------------------------------------------------------
    # Data update helpers
    # ------------------------------------------------------------------

    def _update_kpi_cards(self):
        d = self._report_data
        fin = d.get("financial_summary", {})
        svc = d.get("service_level", {})
        opt = d.get("optimization_summary", {})
        days = d.get("period_days", 90)

        self._kpi_cards["revenue"].update(
            format_currency(fin.get("revenue_period", 0)),
            trend=f"last {days} days",
            color=COLOR_PRIMARY,
        )
        self._kpi_cards["inventory_value"].update(
            format_currency(fin.get("total_inventory_value", 0)), color=COLOR_SUCCESS
        )
        self._kpi_cards["carrying_cost"].update(
            format_currency(fin.get("carrying_cost_monthly", 0)),
            trend="per month",
            color=COLOR_WARNING,
        )
        sr = svc.get("stockout_rate", 0)
        self._kpi_cards["stockout_rate"].update(
            format_percentage(sr),
            trend=f"{svc.get('stockout_count', 0)} SKUs",
            color=COLOR_DANGER if sr > 5 else COLOR_WARNING if sr > 0 else COLOR_SUCCESS,
        )
        savings = opt.get("total_savings", 0)
        self._kpi_cards["savings"].update(
            format_currency(savings),
            trend=f"{opt.get('savings_pct', 0):.1f}% reduction",
            color=COLOR_WARNING if savings > 0 else COLOR_NEUTRAL,
        )
        fr = svc.get("fill_rate", 0)
        self._kpi_cards["fill_rate"].update(
            format_percentage(fr),
            color=COLOR_SUCCESS if fr >= 95 else COLOR_WARNING if fr >= 85 else COLOR_DANGER,
        )

    def _update_trend_chart(self):
        try:
            trend = self._report_data.get("sales_trend", [])
            if not trend:
                self._trend_chart.plot_line([], [], title=t("exec.chart.trend"))
                return
            step = max(1, len(trend) // 12)
            labels = [
                d["date"][-5:] if i % step == 0 else ""
                for i, d in enumerate(trend)
            ]
            revenues = [d["total_revenue"] for d in trend]
            self._trend_chart.plot_line(
                labels, revenues,
                title=t("exec.chart.trend"),
                ylabel="Revenue ($)",
                color=COLOR_PRIMARY,
            )
        except Exception as e:
            self.logger.error(f"Trend chart error: {e}")

    def _update_abc_chart(self):
        try:
            abc = self._report_data.get("abc_summary", [])
            labels = [s["abc_class"] for s in abc]
            values = [s["revenue_pct"] for s in abc]
            colors_map = {"A": COLOR_SUCCESS, "B": COLOR_WARNING, "C": COLOR_NEUTRAL}
            colors = [colors_map.get(lbl, COLOR_PRIMARY) for lbl in labels]

            ax = self._abc_chart._ax
            ax.clear()
            if any(v > 0 for v in values):
                ax.bar(labels, values, color=colors, width=0.5, zorder=3)
                self._abc_chart._style_axis(t("exec.chart.abc"))
                self._abc_chart._figure.tight_layout()
                self._abc_chart._mpl_canvas.draw_idle()
            else:
                self._abc_chart.plot_bar([], [], title=t("exec.chart.abc"))
        except Exception as e:
            self.logger.error(f"ABC chart error: {e}")

    def _load_alert_table(self):
        alerts = self._report_data.get("reorder_alerts", [])
        display = []
        for r in alerts:
            doi = r.get("days_until_stockout")
            display.append({
                **r,
                "days_until_stockout": f"{doi:.0f}" if doi is not None else "\u2014",
                "reorder_point": f"{r.get('reorder_point', 0):.0f}",
            })
        self._alert_table.load_data(display)

    def _load_savings_table(self):
        rows = self._report_data.get("top_savings_skus", [])
        display = []
        for r in rows:
            display.append({
                **r,
                "eoq": f"{r.get('eoq', 0):.0f}",
                "potential_savings": f"{r.get('potential_savings', 0):,.0f}",
                "savings_pct": f"{r.get('savings_pct', 0):.1f}%",
            })
        self._savings_table.load_data(display)

    def _load_products_table(self):
        top = self._report_data.get("top_products", [])
        display = []
        for r in top:
            display.append({
                "id": r.get("id", r.get("product_id", "")),
                "name": r.get("name", r.get("product_name", "")),
                "category": r.get("category", ""),
                "total_revenue": f"{r.get('total_revenue', 0):,.2f}",
                "total_quantity": format_number(r.get("total_quantity", 0)),
            })
        self._products_table.load_data(display)

    # ------------------------------------------------------------------
    # Export actions
    # ------------------------------------------------------------------

    def _export_excel(self):
        """Open save dialog and export the current report to Excel."""
        if not self._report_data:
            messagebox.showwarning("No Data", "Load the dashboard first.")
            return

        filepath = filedialog.asksaveasfilename(
            defaultextension=".xlsx",
            filetypes=[("Excel Workbook", "*.xlsx"), ("All files", "*.*")],
            title="Save Excel Report",
            initialfile="logistics_report.xlsx",
        )
        if not filepath:
            return

        ok = self._report_service.export_to_excel(self._report_data, filepath)
        if ok:
            messagebox.showinfo("Export Complete",
                                f"Excel report saved to:\n{filepath}")
        else:
            messagebox.showerror("Export Failed",
                                 "Could not write Excel file. Check logs for details.")

    def _export_csv(self):
        """Open folder dialog and export the current report as CSV files."""
        if not self._report_data:
            messagebox.showwarning("No Data", "Load the dashboard first.")
            return

        folder = filedialog.askdirectory(title="Select Export Folder")
        if not folder:
            return

        ok = self._report_service.export_to_csv(self._report_data, folder)
        if ok:
            messagebox.showinfo("Export Complete",
                                f"CSV files saved to:\n{folder}")
        else:
            messagebox.showerror("Export Failed",
                                 "Could not write CSV files. Check logs for details.")

    # ------------------------------------------------------------------
    # Stale / language
    # ------------------------------------------------------------------

    def mark_stale(self):
        self._stale = True

    def update_language(self):
        """Refresh all translatable text after a language change."""
        self._lbl_title.configure(text=t("exec.title"))
        self._lbl_period.configure(text=t("common.period"))
        self._btn_excel.configure(text=t("common.export_excel"))
        self._btn_csv.configure(text=t("common.export_csv"))
        self._lbl_alerts.configure(text=t("exec.section.alerts"))
        self._lbl_savings.configure(text=t("exec.section.savings"))
        self._lbl_top_products.configure(text=t("exec.section.top_products"))

        # KPI card labels
        for key, lbl_key in self._kpi_label_keys.items():
            self._kpi_cards[key].set_label(t(lbl_key))

        # Alert table column headers
        _update_tree_headings(self._alert_table, {
            "urgency":            "col.status",
            "product_id":         "col.sku",
            "product_name":       "col.product",
            "current_stock":      "col.stock",
            "days_until_stockout":"col.days_left",
            "reorder_point":      "col.rop",
        })
        # Savings table column headers
        _update_tree_headings(self._savings_table, {
            "product_id":        "col.sku",
            "product_name":      "col.product",
            "eoq":               "col.eoq",
            "potential_savings": "col.savings_dollar",
            "savings_pct":       "col.savings_pct",
        })
        # Products table column headers
        _update_tree_headings(self._products_table, {
            "id":             "col.sku",
            "name":           "col.product",
            "category":       "col.category",
            "total_revenue":  "col.revenue_dollar",
            "total_quantity": "col.units_sold",
        })
        self.mark_stale()


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _update_tree_headings(table: DataTable, col_key_map: dict) -> None:
    """Update Treeview column heading text for each (col_key -> translation_key) pair."""
    for col_key, trans_key in col_key_map.items():
        try:
            table._tree.heading(col_key, text=t(trans_key))
        except Exception:
            pass
