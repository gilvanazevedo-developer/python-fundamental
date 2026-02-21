"""
Import View
Data import management with file picker, import controls, and import history.
"""

import customtkinter as ctk
from sqlalchemy import func

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.database.connection import get_db_manager
from src.database.models import ImportLog
from src.ui.components.import_dialog import ImportDialog
from src.ui.components.data_table import DataTable
from src.ui.theme import (
    FONT_SUBHEADER,
    SECTION_PADDING,
)
from src.logger import LoggerMixin
from typing import Optional, Callable


class ImportView(ctk.CTkFrame, LoggerMixin):
    """Data import management screen."""

    def __init__(
        self,
        master,
        on_import_complete: Optional[Callable] = None,
        **kwargs,
    ):
        super().__init__(master, fg_color="transparent", **kwargs)

        self._on_import_complete = on_import_complete
        self._build()

    def _build(self):
        """Build the import view layout."""
        # Scrollable container
        scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        scroll.pack(fill="both", expand=True)

        # Import dialog
        self._import_dialog = ImportDialog(
            scroll,
            on_import_complete=self._handle_import_complete,
        )
        self._import_dialog.pack(
            fill="x", padx=SECTION_PADDING, pady=(SECTION_PADDING, 10)
        )

        # Import history
        history_label = ctk.CTkLabel(
            scroll, text="Import History", font=FONT_SUBHEADER, anchor="w"
        )
        history_label.pack(fill="x", padx=SECTION_PADDING, pady=(10, 5))

        self._history_table = DataTable(
            scroll,
            columns=[
                {"key": "filename", "label": "File", "width": 200},
                {"key": "data_type", "label": "Type", "width": 100},
                {"key": "records_total", "label": "Total", "width": 70, "anchor": "center"},
                {"key": "records_imported", "label": "Imported", "width": 80, "anchor": "center"},
                {"key": "records_failed", "label": "Failed", "width": 70, "anchor": "center"},
                {"key": "status", "label": "Status", "width": 80, "anchor": "center"},
                {"key": "imported_at", "label": "Date", "width": 150},
            ],
            height=10,
        )
        self._history_table.pack(
            fill="x", padx=SECTION_PADDING, pady=(0, SECTION_PADDING)
        )

    def refresh(self):
        """Refresh import history."""
        self._load_history()

    def _load_history(self):
        """Load import history from database."""
        try:
            db = get_db_manager()
            with db.get_session() as session:
                logs = (
                    session.query(ImportLog)
                    .order_by(ImportLog.imported_at.desc())
                    .limit(50)
                    .all()
                )

                data = [
                    {
                        "filename": log.filename,
                        "data_type": log.data_type.capitalize(),
                        "records_total": log.records_total,
                        "records_imported": log.records_imported,
                        "records_failed": log.records_failed,
                        "status": log.status.capitalize(),
                        "imported_at": str(log.imported_at)[:19] if log.imported_at else "",
                    }
                    for log in logs
                ]

            self._history_table.load_data(data)

        except Exception as e:
            self.logger.error(f"Failed to load import history: {e}")

    def _handle_import_complete(self):
        """Called after a successful import."""
        self._load_history()
        if self._on_import_complete:
            self._on_import_complete()

    def mark_stale(self):
        """Mark view for refresh on next display."""
        pass  # Import view always refreshes
