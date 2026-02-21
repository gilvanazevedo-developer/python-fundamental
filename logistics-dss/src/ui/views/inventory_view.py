"""
Inventory View
Detailed stock table with product listing and detail panel.
"""

import customtkinter as ctk

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.services.inventory_service import InventoryService
from src.services.kpi_service import KPIService
from src.ui.components.data_table import DataTable
from src.ui.components.filter_bar import FilterBar
from src.ui.theme import (
    FONT_SUBHEADER,
    FONT_BODY,
    FONT_SMALL,
    COLOR_PRIMARY,
    COLOR_SUCCESS,
    COLOR_WARNING,
    COLOR_DANGER,
    COLOR_NEUTRAL,
    SECTION_PADDING,
    format_number,
    format_currency,
)
from src.i18n import t
from src.logger import LoggerMixin


class InventoryView(ctk.CTkFrame, LoggerMixin):
    """Detailed inventory table with product detail panel."""

    def __init__(self, master, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)

        self._inventory_service = InventoryService()
        self._kpi_service = KPIService()
        self._stale = True
        self._build()

    def _build(self):
        """Build the inventory view layout."""
        # Filter bar
        self._filter_bar = FilterBar(
            self,
            on_filter_change=self._apply_filters,
            show_period=False,
        )
        self._filter_bar.pack(
            fill="x", padx=SECTION_PADDING, pady=(SECTION_PADDING, 10)
        )

        # Main content: table + detail panel
        content = ctk.CTkFrame(self, fg_color="transparent")
        content.pack(fill="both", expand=True, padx=SECTION_PADDING)
        content.grid_rowconfigure(0, weight=3)
        content.grid_rowconfigure(1, weight=1)
        content.grid_columnconfigure(0, weight=1)

        # Data table
        self._table = DataTable(
            content,
            columns=[
                {"key": "id",          "label": t("col.sku"),          "width": 90},
                {"key": "name",        "label": t("col.product_name"), "width": 200},
                {"key": "category",    "label": t("col.category"),     "width": 110},
                {"key": "total_stock", "label": t("col.stock"),        "width": 80,  "anchor": "center"},
                {"key": "unit_cost",   "label": t("col.unit_cost"),    "width": 90,  "anchor": "e"},
                {"key": "unit_price",  "label": t("col.unit_price"),   "width": 90,  "anchor": "e"},
                {"key": "stock_value", "label": t("col.stock_value"),  "width": 110, "anchor": "e"},
            ],
            on_select=self._on_product_select,
            height=18,
        )
        self._table.grid(row=0, column=0, sticky="nsew", pady=(0, 10))

        # Detail panel
        self._detail_frame = ctk.CTkFrame(content)
        self._detail_frame.grid(row=1, column=0, sticky="nsew", pady=(0, SECTION_PADDING))
        self._build_detail_panel()

    def _build_detail_panel(self):
        """Build the product detail panel."""
        self._detail_title = ctk.CTkLabel(
            self._detail_frame,
            text=t("inv.detail.placeholder"),
            font=FONT_SUBHEADER,
            anchor="w",
        )
        self._detail_title.pack(fill="x", padx=SECTION_PADDING, pady=(SECTION_PADDING, 5))

        self._detail_info = ctk.CTkLabel(
            self._detail_frame,
            text="",
            font=FONT_BODY,
            anchor="w",
            justify="left",
        )
        self._detail_info.pack(fill="x", padx=SECTION_PADDING, pady=(0, 5))

        self._detail_warehouses = ctk.CTkLabel(
            self._detail_frame,
            text="",
            font=FONT_SMALL,
            anchor="w",
            justify="left",
            text_color=COLOR_NEUTRAL,
        )
        self._detail_warehouses.pack(
            fill="x", padx=SECTION_PADDING, pady=(0, SECTION_PADDING)
        )

    def refresh(self):
        """Refresh inventory data."""
        if not self._stale:
            return
        self._stale = False

        try:
            categories = self._inventory_service.get_categories()
            warehouses = self._inventory_service.get_warehouses()
            self._filter_bar.set_categories(categories)
            self._filter_bar.set_warehouses(warehouses)

            filters = self._filter_bar.get_filters()
            self._load_data(filters)
        except Exception as e:
            self.logger.error(f"Inventory refresh failed: {e}")

    def _apply_filters(self, filters: dict):
        """Re-query data with filters."""
        self._load_data(filters)

    def _load_data(self, filters: dict):
        """Load product data into the table."""
        try:
            products = self._inventory_service.get_all_products(
                category=filters.get("category"),
                warehouse_id=filters.get("warehouse_id"),
                search=filters.get("search"),
            )

            # Format numeric values for display
            for p in products:
                p["unit_cost"] = f"${p['unit_cost']:,.2f}"
                p["unit_price"] = f"${p['unit_price']:,.2f}"
                p["stock_value"] = f"${p['stock_value']:,.2f}"

            self._table.load_data(products)

        except Exception as e:
            self.logger.error(f"Inventory data load failed: {e}")

    def _on_product_select(self, row: dict):
        """Handle product row selection to show detail."""
        product_id = row.get("id", "")
        if not product_id:
            return

        try:
            kpis = self._kpi_service.get_product_kpis(product_id)

            self._detail_title.configure(
                text=f"{product_id} - {row.get('name', '')}"
            )

            total_stock = kpis.get("total_stock", 0)
            wh_count = kpis.get("warehouse_count", 0)
            avg_demand = kpis.get("avg_daily_demand", 0)
            dos = kpis.get("days_of_supply")
            dos_text = f"{dos:.0f} days" if dos else "N/A"

            info_text = (
                f"Stock: {format_number(total_stock)} units across {wh_count} warehouse(s)  |  "
                f"Avg Daily Sales: {avg_demand:.1f} units  |  "
                f"Days of Supply: {dos_text}"
            )
            self._detail_info.configure(text=info_text)

            # Warehouse breakdown
            warehouses = kpis.get("warehouses", [])
            wh_lines = []
            for w in warehouses:
                wh_lines.append(
                    f"  {w['warehouse_id']} ({w['warehouse_name']}): "
                    f"{format_number(w['quantity'])} units"
                )
            self._detail_warehouses.configure(
                text="\n".join(wh_lines) if wh_lines else "No warehouse data"
            )

        except Exception as e:
            self.logger.error(f"Product detail load failed: {e}")
            self._detail_title.configure(text=f"{product_id}")
            self._detail_info.configure(text="Error loading details")
            self._detail_warehouses.configure(text="")

    def mark_stale(self):
        """Mark view for refresh on next display."""
        self._stale = True

    def update_language(self):
        """Refresh all translatable text after a language change."""
        _update_tree_headings(self._table, {
            "id":          "col.sku",
            "name":        "col.product_name",
            "category":    "col.category",
            "total_stock": "col.stock",
            "unit_cost":   "col.unit_cost",
            "unit_price":  "col.unit_price",
            "stock_value": "col.stock_value",
        })
        # Reset placeholder only when no product is selected
        current = self._detail_title.cget("text")
        import re
        if not re.search(r" - ", current):
            self._detail_title.configure(text=t("inv.detail.placeholder"))
        self.mark_stale()


def _update_tree_headings(table, col_key_map: dict) -> None:
    from src.i18n import t as _t
    for col_key, trans_key in col_key_map.items():
        try:
            table._tree.heading(col_key, text=_t(trans_key))
        except Exception:
            pass
