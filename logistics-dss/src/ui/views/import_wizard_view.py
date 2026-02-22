"""
Import Wizard View
Five-step guided import: Type → File → Validate → Options → Execute.
Only accessible to ADMIN role.
"""

import sys
from pathlib import Path
from tkinter import filedialog
from typing import Optional

import customtkinter as ctk

PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.services.import_wizard_service import ImportWizardService, ImportValidationError
from src.services.auth_service import AuthService
from src.ui.components.data_table import DataTable
from src.ui.theme import (
    COLOR_PRIMARY,
    COLOR_SUCCESS,
    COLOR_DANGER,
    COLOR_WARNING,
    COLOR_NEUTRAL,
    FONT_SUBHEADER,
    FONT_BODY,
    FONT_SMALL,
    SECTION_PADDING,
)
from src.logger import LoggerMixin
from config.constants import (
    ROLE_ADMIN,
    IMPORT_TYPE_PRODUCTS,
    IMPORT_TYPE_DEMAND,
    IMPORT_TYPE_SUPPLIERS,
)

_IMPORT_TYPES = {
    IMPORT_TYPE_PRODUCTS:  "Product Master (SKU, Name, Cost…)",
    IMPORT_TYPE_DEMAND:    "Demand History (SKU, Date, Qty)",
    IMPORT_TYPE_SUPPLIERS: "Supplier Master (Name, Lead Time…)",
}


class ImportWizardView(ctk.CTkFrame, LoggerMixin):
    """Five-step guided import wizard (ADMIN only)."""

    def __init__(self, master, current_user=None, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self._svc = ImportWizardService()
        self._current_user = current_user
        self._stale = True

        # Wizard state
        self._step = 0
        self._import_type: Optional[str] = None
        self._file_path: Optional[str] = None
        self._validation_result: Optional[dict] = None
        self._overwrite = ctk.BooleanVar(value=False)

        self._build()

    # ------------------------------------------------------------------
    # Layout
    # ------------------------------------------------------------------

    def _build(self):
        user = self._current_user or AuthService.get_current_user()
        is_admin = user and user.role == ROLE_ADMIN

        if not is_admin:
            ctk.CTkLabel(
                self,
                text="Access Denied — Administrator role required.",
                font=FONT_SUBHEADER,
                text_color=COLOR_DANGER,
            ).pack(expand=True)
            return

        # Step frames (only one visible at a time)
        self._steps: list[ctk.CTkFrame] = []
        self._steps.append(self._build_step1())
        self._steps.append(self._build_step2())
        self._steps.append(self._build_step3())
        self._steps.append(self._build_step4())
        self._steps.append(self._build_step5())

        for frame in self._steps:
            frame.pack(fill="both", expand=True)

        self._show_step(0)

    # --- Step 1: Select Import Type ---

    def _build_step1(self) -> ctk.CTkFrame:
        frame = ctk.CTkFrame(self, fg_color="transparent")
        ctk.CTkLabel(frame, text="Step 1 — Select Import Type", font=FONT_SUBHEADER).pack(
            pady=(30, 20)
        )
        self._type_var = ctk.StringVar(value=IMPORT_TYPE_PRODUCTS)
        for itype, label in _IMPORT_TYPES.items():
            ctk.CTkRadioButton(
                frame, text=label, variable=self._type_var, value=itype, font=FONT_BODY
            ).pack(pady=6)

        ctk.CTkButton(
            frame, text="Next →", width=120, command=lambda: self._go_to(1)
        ).pack(pady=20)
        return frame

    # --- Step 2: Select File ---

    def _build_step2(self) -> ctk.CTkFrame:
        frame = ctk.CTkFrame(self, fg_color="transparent")
        ctk.CTkLabel(frame, text="Step 2 — Select File", font=FONT_SUBHEADER).pack(pady=(30, 20))

        file_row = ctk.CTkFrame(frame, fg_color="transparent")
        file_row.pack()
        self._file_label = ctk.CTkLabel(file_row, text="No file selected", font=FONT_SMALL, width=300, anchor="w")
        self._file_label.grid(row=0, column=0, padx=(0, 8))
        ctk.CTkButton(file_row, text="Browse…", width=90, command=self._browse_file).grid(row=0, column=1)

        self._file_info_label = ctk.CTkLabel(frame, text="", font=FONT_SMALL, text_color=COLOR_NEUTRAL)
        self._file_info_label.pack(pady=8)

        btn_row = ctk.CTkFrame(frame, fg_color="transparent")
        btn_row.pack(pady=10)
        ctk.CTkButton(btn_row, text="← Back", width=100, fg_color=COLOR_NEUTRAL,
                      command=lambda: self._go_to(0)).grid(row=0, column=0, padx=5)
        ctk.CTkButton(btn_row, text="Next →", width=100,
                      command=lambda: self._go_to(2)).grid(row=0, column=1, padx=5)
        return frame

    # --- Step 3: Validation & Preview ---

    def _build_step3(self) -> ctk.CTkFrame:
        frame = ctk.CTkFrame(self, fg_color="transparent")
        ctk.CTkLabel(frame, text="Step 3 — Validation & Preview", font=FONT_SUBHEADER).pack(pady=(20, 8))

        self._val_summary = ctk.CTkLabel(frame, text="", font=FONT_SMALL)
        self._val_summary.pack(pady=4)

        self._val_errors = ctk.CTkLabel(
            frame, text="", font=FONT_SMALL, text_color=COLOR_DANGER, wraplength=600
        )
        self._val_errors.pack(pady=4)

        self._preview_table = DataTable(
            frame,
            columns=[
                {"key": col, "label": col, "width": 100}
                for col in ["col1", "col2", "col3", "col4", "col5"]
            ],
            height=10,
        )
        self._preview_table.pack(fill="x", padx=SECTION_PADDING)

        btn_row = ctk.CTkFrame(frame, fg_color="transparent")
        btn_row.pack(pady=10)
        ctk.CTkButton(btn_row, text="← Back", width=100, fg_color=COLOR_NEUTRAL,
                      command=lambda: self._go_to(1)).grid(row=0, column=0, padx=5)
        self._step3_next = ctk.CTkButton(btn_row, text="Next →", width=100,
                                         command=lambda: self._go_to(3))
        self._step3_next.grid(row=0, column=1, padx=5)
        return frame

    # --- Step 4: Options ---

    def _build_step4(self) -> ctk.CTkFrame:
        frame = ctk.CTkFrame(self, fg_color="transparent")
        ctk.CTkLabel(frame, text="Step 4 — Options", font=FONT_SUBHEADER).pack(pady=(30, 20))

        ctk.CTkCheckBox(
            frame,
            text="Overwrite existing records",
            variable=self._overwrite,
            font=FONT_BODY,
        ).pack(pady=10)

        btn_row = ctk.CTkFrame(frame, fg_color="transparent")
        btn_row.pack(pady=10)
        ctk.CTkButton(btn_row, text="← Back", width=100, fg_color=COLOR_NEUTRAL,
                      command=lambda: self._go_to(2)).grid(row=0, column=0, padx=5)
        ctk.CTkButton(btn_row, text="Next →", width=100,
                      command=lambda: self._go_to(4)).grid(row=0, column=1, padx=5)
        return frame

    # --- Step 5: Execute ---

    def _build_step5(self) -> ctk.CTkFrame:
        frame = ctk.CTkFrame(self, fg_color="transparent")
        ctk.CTkLabel(frame, text="Step 5 — Import", font=FONT_SUBHEADER).pack(pady=(30, 20))

        self._progress = ctk.CTkProgressBar(frame, width=400)
        self._progress.pack(pady=10)
        self._progress.set(0)

        self._import_status = ctk.CTkLabel(frame, text="Ready to import.", font=FONT_BODY)
        self._import_status.pack(pady=8)

        btn_row = ctk.CTkFrame(frame, fg_color="transparent")
        btn_row.pack(pady=10)
        ctk.CTkButton(btn_row, text="← Back", width=100, fg_color=COLOR_NEUTRAL,
                      command=lambda: self._go_to(3)).grid(row=0, column=0, padx=5)
        self._import_btn = ctk.CTkButton(btn_row, text="Start Import", width=120,
                                         command=self._run_import)
        self._import_btn.grid(row=0, column=1, padx=5)
        ctk.CTkButton(btn_row, text="Close", width=100, fg_color=COLOR_NEUTRAL,
                      command=self._reset_wizard).grid(row=0, column=2, padx=5)
        return frame

    # ------------------------------------------------------------------
    # Navigation
    # ------------------------------------------------------------------

    def _show_step(self, step: int):
        for i, frame in enumerate(self._steps):
            if i == step:
                frame.lift()
            else:
                frame.lower()
        self._step = step

    def _go_to(self, step: int):
        if step == 2:
            self._run_validation()
        self._show_step(step)

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    def _browse_file(self):
        path = filedialog.askopenfilename(
            title="Select Import File",
            filetypes=[("CSV/Excel files", "*.csv *.xlsx *.xls"), ("All files", "*.*")],
        )
        if path:
            self._file_path = path
            self._file_label.configure(text=path[-50:])
            self._file_info_label.configure(text=f"Detected format: {Path(path).suffix.upper()}")

    def _run_validation(self):
        if not self._file_path:
            return

        self._import_type = self._type_var.get()
        try:
            if self._import_type == IMPORT_TYPE_PRODUCTS:
                result = self._svc.validate_product_file(self._file_path)
            elif self._import_type == IMPORT_TYPE_DEMAND:
                result = self._svc.validate_demand_file(self._file_path)
            else:
                result = self._svc.validate_supplier_file(self._file_path)

            self._validation_result = result

            errors = result.get("errors", [])
            warnings = result.get("warnings", [])
            row_count = result.get("row_count", 0)

            self._val_summary.configure(
                text=f"✓ {row_count - len(errors)} rows valid    "
                     f"⚠ {len(warnings)} warnings    "
                     f"✗ {len(errors)} errors"
            )

            if errors:
                self._val_errors.configure(text="\n".join(errors[:5]))
                self._step3_next.configure(state="disabled")
            else:
                self._val_errors.configure(text="")
                self._step3_next.configure(state="normal")

            # Preview
            preview_rows = self._svc.get_import_preview(self._file_path, self._import_type)
            if preview_rows:
                keys = list(preview_rows[0].keys())[:5]
                # Rebuild preview table columns
                self._preview_table._tree.delete(*self._preview_table._tree.get_children())
                for k in keys:
                    self._preview_table._tree.heading(k if k in [c["key"] for c in self._preview_table._columns] else "col1", text=k)
                # Load data
                display = [{f"col{i+1}": str(row.get(k, "")) for i, k in enumerate(keys)} for row in preview_rows]
                self._preview_table.load_data(display)

        except ImportValidationError as exc:
            self._val_summary.configure(text="✗ Validation error")
            self._val_errors.configure(text=str(exc))
            self._step3_next.configure(state="disabled")
        except Exception as exc:
            self.logger.error(f"Validation failed: {exc}")
            self._val_errors.configure(text=f"Error: {exc}")

    def _run_import(self):
        if not self._file_path or not self._import_type:
            return

        self._import_btn.configure(state="disabled")
        self._progress.set(0.1)
        self.update_idletasks()

        try:
            overwrite = self._overwrite.get()
            if self._import_type == IMPORT_TYPE_PRODUCTS:
                result = self._svc.import_products(self._file_path, overwrite_existing=overwrite)
            elif self._import_type == IMPORT_TYPE_DEMAND:
                result = self._svc.import_demand_history(self._file_path)
            else:
                result = self._svc.import_suppliers(self._file_path)

            self._progress.set(1.0)
            imported = result.get("imported_count", 0)
            skipped  = result.get("skipped_count", 0)
            errors   = result.get("errors", [])
            self._import_status.configure(
                text=f"✓ Imported: {imported}    ⊘ Skipped: {skipped}    "
                     f"✗ Errors: {len(errors)}"
            )

        except Exception as exc:
            self.logger.error(f"Import failed: {exc}")
            self._import_status.configure(text=f"Import failed: {exc}")
            self._progress.set(0)
            self._import_btn.configure(state="normal")

    def _reset_wizard(self):
        self._file_path = None
        self._import_type = None
        self._validation_result = None
        self._overwrite.set(False)
        self._progress.set(0)
        self._import_status.configure(text="Ready to import.")
        self._show_step(0)

    # ------------------------------------------------------------------
    # View lifecycle
    # ------------------------------------------------------------------

    def refresh(self):
        if not self._stale:
            return
        self._stale = False

    def mark_stale(self):
        self._stale = True

    def update_language(self):
        pass
