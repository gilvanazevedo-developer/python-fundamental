"""
Filter Bar Widget
Horizontal control strip for filtering dashboard data.
"""

from typing import Callable, Optional, List, Dict, Any

import customtkinter as ctk

from src.ui.theme import FONT_SMALL, FONT_BODY, COMPONENT_GAP


class FilterBar(ctk.CTkFrame):
    """Filter bar with category, warehouse, search, and period controls."""

    def __init__(
        self,
        master,
        on_filter_change: Optional[Callable] = None,
        show_period: bool = True,
        **kwargs,
    ):
        super().__init__(master, fg_color="transparent", **kwargs)

        self._on_filter_change = on_filter_change
        self._categories: List[str] = []
        self._warehouses: List[Dict[str, Any]] = []

        self._build(show_period)

    def _build(self, show_period: bool):
        """Build filter controls."""
        # Category
        cat_label = ctk.CTkLabel(self, text="Category:", font=FONT_SMALL)
        cat_label.pack(side="left", padx=(0, 3))

        self._category_var = ctk.StringVar(value="All")
        self._category_menu = ctk.CTkOptionMenu(
            self,
            variable=self._category_var,
            values=["All"],
            command=self._on_change,
            width=130,
            height=28,
        )
        self._category_menu.pack(side="left", padx=(0, COMPONENT_GAP))

        # Warehouse
        wh_label = ctk.CTkLabel(self, text="Warehouse:", font=FONT_SMALL)
        wh_label.pack(side="left", padx=(0, 3))

        self._warehouse_var = ctk.StringVar(value="All")
        self._warehouse_menu = ctk.CTkOptionMenu(
            self,
            variable=self._warehouse_var,
            values=["All"],
            command=self._on_change,
            width=130,
            height=28,
        )
        self._warehouse_menu.pack(side="left", padx=(0, COMPONENT_GAP))

        # Search
        search_label = ctk.CTkLabel(self, text="Search:", font=FONT_SMALL)
        search_label.pack(side="left", padx=(0, 3))

        self._search_var = ctk.StringVar()
        self._search_entry = ctk.CTkEntry(
            self,
            textvariable=self._search_var,
            placeholder_text="Product name or ID...",
            width=180,
            height=28,
        )
        self._search_entry.pack(side="left", padx=(0, COMPONENT_GAP))
        self._search_entry.bind("<Return>", lambda e: self._on_change(None))

        # Period selector
        if show_period:
            period_label = ctk.CTkLabel(self, text="Period:", font=FONT_SMALL)
            period_label.pack(side="left", padx=(0, 3))

            self._period_var = ctk.StringVar(value="Last 30 days")
            self._period_menu = ctk.CTkOptionMenu(
                self,
                variable=self._period_var,
                values=["Last 7 days", "Last 14 days", "Last 30 days", "Last 60 days", "Last 90 days"],
                command=self._on_change,
                width=130,
                height=28,
            )
            self._period_menu.pack(side="left", padx=(0, COMPONENT_GAP))

        # Refresh button
        self._refresh_btn = ctk.CTkButton(
            self,
            text="Refresh",
            width=80,
            height=28,
            command=lambda: self._on_change(None),
        )
        self._refresh_btn.pack(side="right", padx=(0, 5))

    def set_categories(self, categories: List[str]):
        """Update the category dropdown values."""
        self._categories = categories
        values = ["All"] + categories
        self._category_menu.configure(values=values)

    def set_warehouses(self, warehouses: List[Dict[str, Any]]):
        """Update the warehouse dropdown values."""
        self._warehouses = warehouses
        values = ["All"] + [f"{w['name']}" for w in warehouses]
        self._warehouse_menu.configure(values=values)

    def get_filters(self) -> Dict[str, Any]:
        """Get current filter values."""
        category = self._category_var.get()
        warehouse = self._warehouse_var.get()
        search = self._search_var.get().strip()

        # Map period text to days
        period_text = getattr(self, "_period_var", ctk.StringVar(value="Last 30 days")).get()
        period_map = {
            "Last 7 days": 7,
            "Last 14 days": 14,
            "Last 30 days": 30,
            "Last 60 days": 60,
            "Last 90 days": 90,
        }
        days = period_map.get(period_text, 30)

        # Resolve warehouse name → id
        warehouse_id = None
        if warehouse != "All":
            for w in self._warehouses:
                if w["name"] == warehouse:
                    warehouse_id = w["id"]
                    break

        return {
            "category": category if category != "All" else None,
            "warehouse_id": warehouse_id,
            "search": search if search else None,
            "days": days,
        }

    def _on_change(self, _value):
        """Notify parent of filter change."""
        if self._on_filter_change:
            self._on_filter_change(self.get_filters())
