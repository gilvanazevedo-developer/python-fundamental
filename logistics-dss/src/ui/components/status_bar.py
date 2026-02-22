"""
Status Bar Widget
Bottom bar showing database status and record counts.
"""

from datetime import datetime

import customtkinter as ctk
from sqlalchemy import func

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.database.connection import get_db_manager
from src.database.models import Product, InventoryLevel, SalesRecord
from src.ui.theme import FONT_STATUS, COLOR_SUCCESS, COLOR_NEUTRAL


class StatusBar(ctk.CTkFrame):
    """Bottom status bar showing application state."""

    def __init__(self, master, **kwargs):
        super().__init__(master, height=28, corner_radius=0, **kwargs)

        self._build()

    def _build(self):
        """Build status bar labels."""
        self._db_label = ctk.CTkLabel(
            self, text="DB: --", font=FONT_STATUS, text_color=COLOR_NEUTRAL
        )
        self._db_label.pack(side="left", padx=(10, 20))

        self._products_label = ctk.CTkLabel(
            self, text="Products: --", font=FONT_STATUS, text_color=COLOR_NEUTRAL
        )
        self._products_label.pack(side="left", padx=(0, 20))

        self._sales_label = ctk.CTkLabel(
            self, text="Sales Records: --", font=FONT_STATUS, text_color=COLOR_NEUTRAL
        )
        self._sales_label.pack(side="left", padx=(0, 20))

        self._refresh_label = ctk.CTkLabel(
            self, text="Last refresh: --", font=FONT_STATUS, text_color=COLOR_NEUTRAL
        )
        self._refresh_label.pack(side="right", padx=(0, 10))

    def refresh(self):
        """Update status bar with current data."""
        try:
            db = get_db_manager()
            with db.get_session() as session:
                product_count = session.query(func.count(Product.id)).scalar() or 0
                sales_count = session.query(func.count(SalesRecord.id)).scalar() or 0

            self._db_label.configure(text="DB: Connected", text_color=COLOR_SUCCESS)
            self._products_label.configure(text=f"Products: {product_count:,}")
            self._sales_label.configure(text=f"Sales Records: {sales_count:,}")
            self._refresh_label.configure(
                text=f"Last refresh: {datetime.now().strftime('%H:%M:%S')}"
            )
        except Exception:
            self._db_label.configure(text="DB: Error", text_color="#d64545")
