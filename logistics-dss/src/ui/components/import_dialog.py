"""
Import Dialog Widget
File import controls with data type selection and result display.
"""

from pathlib import Path
from tkinter import filedialog
from typing import Optional, Callable

import customtkinter as ctk

import sys

PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from config.constants import DataType
from config.settings import SUPPORTED_EXTENSIONS
from src.importer.csv_importer import CSVImporter
from src.importer.excel_importer import ExcelImporter
from src.ui.theme import (
    FONT_BODY,
    FONT_SMALL,
    FONT_SUBHEADER,
    COLOR_SUCCESS,
    COLOR_DANGER,
    COLOR_WARNING,
    SECTION_PADDING,
)
from src.logger import LoggerMixin


class ImportDialog(ctk.CTkFrame, LoggerMixin):
    """File import controls with progress and result feedback."""

    def __init__(
        self,
        master,
        on_import_complete: Optional[Callable] = None,
        **kwargs,
    ):
        super().__init__(master, **kwargs)

        self._on_import_complete = on_import_complete
        self._selected_file: Optional[Path] = None

        self._build()

    def _build(self):
        """Build import controls."""
        title = ctk.CTkLabel(self, text="Import Data", font=FONT_SUBHEADER, anchor="w")
        title.pack(fill="x", padx=SECTION_PADDING, pady=(SECTION_PADDING, 10))

        # Data type selector
        type_frame = ctk.CTkFrame(self, fg_color="transparent")
        type_frame.pack(fill="x", padx=SECTION_PADDING, pady=(0, 5))

        type_label = ctk.CTkLabel(type_frame, text="Data Type:", font=FONT_BODY)
        type_label.pack(side="left", padx=(0, 5))

        self._type_var = ctk.StringVar(value="Products")
        self._type_menu = ctk.CTkOptionMenu(
            type_frame,
            variable=self._type_var,
            values=["Products", "Inventory", "Sales", "Suppliers", "Warehouses"],
            width=150,
            height=30,
        )
        self._type_menu.pack(side="left")

        # File selection
        file_frame = ctk.CTkFrame(self, fg_color="transparent")
        file_frame.pack(fill="x", padx=SECTION_PADDING, pady=(0, 5))

        self._browse_btn = ctk.CTkButton(
            file_frame,
            text="Browse...",
            width=100,
            height=30,
            command=self._browse_file,
        )
        self._browse_btn.pack(side="left", padx=(0, 10))

        self._file_label = ctk.CTkLabel(
            file_frame,
            text="No file selected",
            font=FONT_SMALL,
            anchor="w",
        )
        self._file_label.pack(side="left", fill="x", expand=True)

        # Import button
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(fill="x", padx=SECTION_PADDING, pady=(5, 10))

        self._import_btn = ctk.CTkButton(
            btn_frame,
            text="Import",
            width=120,
            height=35,
            command=self._run_import,
            state="disabled",
        )
        self._import_btn.pack(side="left")

        # Result display
        self._result_label = ctk.CTkLabel(
            self,
            text="",
            font=FONT_SMALL,
            anchor="w",
            wraplength=500,
        )
        self._result_label.pack(
            fill="x", padx=SECTION_PADDING, pady=(0, SECTION_PADDING)
        )

    def _browse_file(self):
        """Open file dialog to select a file."""
        filetypes = [
            ("Supported files", "*.csv *.xlsx *.xls"),
            ("CSV files", "*.csv"),
            ("Excel files", "*.xlsx *.xls"),
        ]
        filepath = filedialog.askopenfilename(filetypes=filetypes)
        if filepath:
            self._selected_file = Path(filepath)
            self._file_label.configure(text=self._selected_file.name)
            self._import_btn.configure(state="normal")

    def _get_data_type(self) -> DataType:
        """Map the dropdown selection to DataType enum."""
        type_map = {
            "Products": DataType.PRODUCTS,
            "Inventory": DataType.INVENTORY,
            "Sales": DataType.SALES,
            "Suppliers": DataType.SUPPLIERS,
            "Warehouses": DataType.WAREHOUSES,
        }
        return type_map[self._type_var.get()]

    def _run_import(self):
        """Execute the import."""
        if not self._selected_file:
            return

        self._import_btn.configure(state="disabled", text="Importing...")
        self._result_label.configure(text="Importing...", text_color=("gray10", "gray90"))
        self.update_idletasks()

        try:
            data_type = self._get_data_type()
            suffix = self._selected_file.suffix.lower()

            if suffix == ".csv":
                importer = CSVImporter(data_type)
            else:
                importer = ExcelImporter(data_type)

            result = importer.import_file(self._selected_file)

            # Display result
            if result.success and result.failed_records == 0:
                color = COLOR_SUCCESS
                status = "Success"
            elif result.success:
                color = COLOR_WARNING
                status = "Partial"
            else:
                color = COLOR_DANGER
                status = "Failed"

            msg = (
                f"{status}: {result.imported_records}/{result.total_records} records imported"
            )
            if result.failed_records > 0:
                msg += f", {result.failed_records} failed"
            if result.errors:
                first_error = result.errors[0].get("message", "")
                if first_error:
                    msg += f"\nFirst error: {first_error}"

            self._result_label.configure(text=msg, text_color=color)
            self.logger.info(f"Import complete: {msg}")

            if result.success and self._on_import_complete:
                self._on_import_complete()

        except Exception as e:
            self._result_label.configure(
                text=f"Error: {str(e)}", text_color=COLOR_DANGER
            )
            self.logger.error(f"Import error: {e}")

        finally:
            self._import_btn.configure(state="normal", text="Import")
