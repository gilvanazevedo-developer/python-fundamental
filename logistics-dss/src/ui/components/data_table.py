"""
Data Table Widget
Sortable, selectable data table using tkinter Treeview.
"""

import tkinter as tk
from tkinter import ttk
from typing import List, Dict, Any, Callable, Optional

import customtkinter as ctk

from src.ui.theme import (
    COLOR_DANGER,
    FONT_TABLE,
    FONT_TABLE_HEADER,
    TABLE_ROW_HEIGHT,
    SECTION_PADDING,
)


class DataTable(ctk.CTkFrame):
    """Sortable data table with row selection."""

    def __init__(
        self,
        master,
        columns: List[Dict[str, Any]] = None,
        on_select: Optional[Callable] = None,
        height: int = 15,
        **kwargs,
    ):
        """
        Initialize data table.

        Args:
            columns: List of {"key": str, "label": str, "width": int, "anchor": str}
            on_select: Callback when a row is selected, receives row dict
            height: Number of visible rows
        """
        super().__init__(master, **kwargs)

        self._columns = columns or []
        self._on_select = on_select
        self._data: List[Dict[str, Any]] = []
        self._sort_column = None
        self._sort_reverse = False

        self._build(height)

    def _build(self, height: int):
        """Build the treeview widget."""
        # Configure treeview style
        style = ttk.Style()
        style.configure(
            "DataTable.Treeview",
            rowheight=TABLE_ROW_HEIGHT,
            font=FONT_TABLE,
        )
        style.configure(
            "DataTable.Treeview.Heading",
            font=FONT_TABLE_HEADER,
        )

        # Column keys
        col_keys = [c["key"] for c in self._columns]

        # Frame for treeview + scrollbar
        tree_frame = ctk.CTkFrame(self, fg_color="transparent")
        tree_frame.pack(fill="both", expand=True, padx=5, pady=5)

        # Scrollbar
        scrollbar = ttk.Scrollbar(tree_frame, orient="vertical")
        scrollbar.pack(side="right", fill="y")

        # Treeview
        self._tree = ttk.Treeview(
            tree_frame,
            columns=col_keys,
            show="headings",
            height=height,
            style="DataTable.Treeview",
            yscrollcommand=scrollbar.set,
            selectmode="browse",
        )
        self._tree.pack(fill="both", expand=True)
        scrollbar.config(command=self._tree.yview)

        # Configure columns
        for col in self._columns:
            key = col["key"]
            label = col.get("label", key)
            width = col.get("width", 100)
            anchor = col.get("anchor", "w")

            self._tree.heading(
                key,
                text=label,
                command=lambda c=key: self._sort_by(c),
            )
            self._tree.column(key, width=width, anchor=anchor, minwidth=50)

        # Bind selection
        self._tree.bind("<<TreeviewSelect>>", self._on_row_select)

    def load_data(self, data: List[Dict[str, Any]]):
        """Populate the table with data."""
        self._data = data
        self._refresh_display()

    def _refresh_display(self):
        """Redraw all rows."""
        self._tree.delete(*self._tree.get_children())

        col_keys = [c["key"] for c in self._columns]
        for row_data in self._data:
            values = [row_data.get(k, "") for k in col_keys]
            item = self._tree.insert("", "end", values=values)

            # Highlight zero-stock rows
            stock_val = row_data.get("total_stock", row_data.get("quantity"))
            if stock_val is not None and int(stock_val) == 0:
                self._tree.item(item, tags=("stockout",))

        self._tree.tag_configure("stockout", foreground=COLOR_DANGER)

    def _sort_by(self, column: str):
        """Sort table by a column."""
        if self._sort_column == column:
            self._sort_reverse = not self._sort_reverse
        else:
            self._sort_column = column
            self._sort_reverse = False

        def sort_key(row):
            val = row.get(column, "")
            try:
                return float(val)
            except (ValueError, TypeError):
                return str(val).lower()

        self._data.sort(key=sort_key, reverse=self._sort_reverse)
        self._refresh_display()

    def _on_row_select(self, event):
        """Handle row selection."""
        selection = self._tree.selection()
        if not selection or not self._on_select:
            return

        item = selection[0]
        values = self._tree.item(item, "values")
        col_keys = [c["key"] for c in self._columns]

        row_dict = {}
        for i, key in enumerate(col_keys):
            row_dict[key] = values[i] if i < len(values) else ""

        self._on_select(row_dict)

    def clear(self):
        """Remove all rows."""
        self._data = []
        self._tree.delete(*self._tree.get_children())

    def get_selected(self) -> Optional[Dict[str, Any]]:
        """Return the currently selected row data."""
        selection = self._tree.selection()
        if not selection:
            return None

        item = selection[0]
        values = self._tree.item(item, "values")
        col_keys = [c["key"] for c in self._columns]

        return {key: values[i] if i < len(values) else "" for i, key in enumerate(col_keys)}
