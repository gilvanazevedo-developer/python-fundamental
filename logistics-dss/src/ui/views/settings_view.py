"""
Settings View
General settings, scheduled reports panel (ADMIN only), and user management (ADMIN only).
"""

import sys
from pathlib import Path
from typing import Optional

import customtkinter as ctk

PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.services.settings_service import SettingsService
from src.services.scheduler_service import SchedulerService
from src.services.auth_service import AuthService
from src.repositories.user_repository import UserRepository
from src.ui.components.data_table import DataTable
from src.ui.theme import (
    COLOR_PRIMARY,
    COLOR_SUCCESS,
    COLOR_DANGER,
    COLOR_NEUTRAL,
    COLOR_WARNING,
    FONT_SUBHEADER,
    FONT_BODY,
    FONT_SMALL,
    SECTION_PADDING,
)
from src.i18n import t
from src.logger import LoggerMixin
from config.constants import ROLE_ADMIN

_LOG_LEVELS = ["DEBUG", "INFO", "WARNING", "ERROR"]
_THEMES = ["dark", "light", "system"]


class SettingsView(ctk.CTkFrame, LoggerMixin):
    """Application settings, scheduled reports, and user management."""

    def __init__(self, master, current_user=None, scheduler: Optional[SchedulerService] = None, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self._settings = SettingsService()
        self._scheduler = scheduler
        self._current_user = current_user
        self._user_repo = UserRepository()
        self._stale = True
        self._build()

    # ------------------------------------------------------------------
    # Layout
    # ------------------------------------------------------------------

    def _build(self):
        user = self._current_user or AuthService.get_current_user()
        is_admin = user and user.role == ROLE_ADMIN

        self._scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self._scroll.pack(fill="both", expand=True)

        ctk.CTkLabel(
            self._scroll, text="Settings", font=FONT_SUBHEADER, anchor="w"
        ).pack(fill="x", padx=SECTION_PADDING, pady=(SECTION_PADDING, 10))

        # ── General Settings ───────────────────────────────────────────
        self._build_general_section()

        # ── Scheduled Reports (ADMIN only) ─────────────────────────────
        if is_admin:
            self._build_schedule_section()

        # ── User Management (ADMIN only) ───────────────────────────────
        if is_admin:
            self._build_user_section()

        # ── Save / Reset buttons ───────────────────────────────────────
        btn_frame = ctk.CTkFrame(self._scroll, fg_color="transparent")
        btn_frame.pack(fill="x", padx=SECTION_PADDING, pady=(10, SECTION_PADDING))
        ctk.CTkButton(
            btn_frame, text="Save Settings", width=140,
            command=self._save_settings,
        ).grid(row=0, column=0, padx=(0, 10))
        ctk.CTkButton(
            btn_frame, text="Reset to Defaults", width=140,
            fg_color=COLOR_NEUTRAL,
            command=self._reset_to_defaults,
        ).grid(row=0, column=1)

    def _build_general_section(self):
        section = ctk.CTkFrame(self._scroll)
        section.pack(fill="x", padx=SECTION_PADDING, pady=(0, 10))

        ctk.CTkLabel(section, text="GENERAL", font=FONT_BODY).pack(
            anchor="w", padx=12, pady=(10, 4)
        )

        row_frame = ctk.CTkFrame(section, fg_color="transparent")
        row_frame.pack(fill="x", padx=12, pady=(0, 10))

        # Log level
        ctk.CTkLabel(row_frame, text="Log level:", font=FONT_SMALL).grid(
            row=0, column=0, padx=(0, 6), sticky="w"
        )
        self._log_level_var = ctk.StringVar(value=self._settings.get("log_level", "INFO"))
        ctk.CTkOptionMenu(
            row_frame, variable=self._log_level_var,
            values=_LOG_LEVELS, width=100, height=28,
        ).grid(row=0, column=1, padx=(0, 20), sticky="w")

        # Theme
        ctk.CTkLabel(row_frame, text="Theme:", font=FONT_SMALL).grid(
            row=0, column=2, padx=(0, 6), sticky="w"
        )
        self._theme_var = ctk.StringVar(value=self._settings.get("theme", "dark"))
        ctk.CTkOptionMenu(
            row_frame, variable=self._theme_var,
            values=_THEMES, width=100, height=28,
            command=lambda v: ctk.set_appearance_mode(v),
        ).grid(row=0, column=3, padx=(0, 20), sticky="w")

        # Export dir
        ctk.CTkLabel(row_frame, text="Export dir:", font=FONT_SMALL).grid(
            row=1, column=0, padx=(0, 6), pady=(8, 0), sticky="w"
        )
        self._export_dir_var = ctk.StringVar(value=self._settings.get("export_dir", "exports/"))
        ctk.CTkEntry(
            row_frame, textvariable=self._export_dir_var, width=260, height=28,
        ).grid(row=1, column=1, columnspan=3, padx=(0, 0), pady=(8, 0), sticky="w")

    def _build_schedule_section(self):
        section = ctk.CTkFrame(self._scroll)
        section.pack(fill="x", padx=SECTION_PADDING, pady=(0, 10))

        header = ctk.CTkFrame(section, fg_color="transparent")
        header.pack(fill="x", padx=12, pady=(10, 4))
        ctk.CTkLabel(header, text="SCHEDULED REPORTS", font=FONT_BODY).pack(side="left")

        self._schedule_table = DataTable(
            section,
            columns=[
                {"key": "report_type",     "label": "Type",       "width": 110},
                {"key": "export_format",   "label": "Format",     "width": 70},
                {"key": "cron_expression", "label": "Cron",       "width": 120},
                {"key": "active",          "label": "Status",     "width": 70},
                {"key": "last_run_at",     "label": "Last Run",   "width": 140},
                {"key": "next_run_time",   "label": "Next Run",   "width": 140},
            ],
            height=6,
        )
        self._schedule_table.pack(fill="x", padx=12, pady=(0, 8))

        btn_row = ctk.CTkFrame(section, fg_color="transparent")
        btn_row.pack(fill="x", padx=12, pady=(0, 10))
        ctk.CTkButton(btn_row, text="+ Add Schedule", width=120, height=26,
                      command=self._add_schedule_dialog).grid(row=0, column=0, padx=(0, 8))
        ctk.CTkButton(btn_row, text="Deactivate", width=100, height=26,
                      fg_color=COLOR_WARNING, command=self._deactivate_selected_schedule
                      ).grid(row=0, column=1)

    def _build_user_section(self):
        section = ctk.CTkFrame(self._scroll)
        section.pack(fill="x", padx=SECTION_PADDING, pady=(0, 10))

        ctk.CTkLabel(section, text="USER MANAGEMENT", font=FONT_BODY).pack(
            anchor="w", padx=12, pady=(10, 4)
        )

        self._user_table = DataTable(
            section,
            columns=[
                {"key": "username",     "label": "Username",     "width": 120},
                {"key": "display_name", "label": "Display Name", "width": 150},
                {"key": "role",         "label": "Role",         "width": 80},
                {"key": "active",       "label": "Active",       "width": 60, "anchor": "center"},
                {"key": "last_login",   "label": "Last Login",   "width": 140},
            ],
            height=6,
        )
        self._user_table.pack(fill="x", padx=12, pady=(0, 8))

        btn_row = ctk.CTkFrame(section, fg_color="transparent")
        btn_row.pack(fill="x", padx=12, pady=(0, 10))
        ctk.CTkButton(btn_row, text="+ Add User", width=100, height=26,
                      command=self._add_user_dialog).grid(row=0, column=0, padx=(0, 8))
        ctk.CTkButton(btn_row, text="Deactivate", width=100, height=26,
                      fg_color=COLOR_DANGER, command=self._deactivate_selected_user
                      ).grid(row=0, column=1)

    # ------------------------------------------------------------------
    # Refresh
    # ------------------------------------------------------------------

    def refresh(self):
        if not self._stale:
            return
        self._stale = False
        self._reload()

    def _reload(self):
        self._load_schedules()
        self._load_users()

    def _load_schedules(self):
        if not hasattr(self, "_schedule_table"):
            return
        try:
            if self._scheduler:
                rows = self._scheduler.get_all_schedules()
            else:
                rows = []
            display = []
            for s in rows:
                display.append({
                    "report_type":     s["report_type"],
                    "export_format":   s["export_format"],
                    "cron_expression": s["cron_expression"],
                    "active":          "Active" if s["active"] else "Inactive",
                    "last_run_at":     (s.get("last_run_at") or "—")[:16].replace("T", " "),
                    "next_run_time":   (s.get("next_run_time") or "—")[:16].replace("T", " "),
                })
            self._schedule_table.load_data(display)
        except Exception as exc:
            self.logger.error(f"Schedule load failed: {exc}")

    def _load_users(self):
        if not hasattr(self, "_user_table"):
            return
        try:
            users = self._user_repo.get_all(active_only=False)
            display = []
            for u in users:
                display.append({
                    "username":     u.username,
                    "display_name": u.display_name or "",
                    "role":         u.role,
                    "active":       "✓" if u.active else "✗",
                    "last_login":   str(u.last_login_at)[:16].replace("T", " ") if u.last_login_at else "Never",
                })
            self._user_table.load_data(display)
        except Exception as exc:
            self.logger.error(f"User load failed: {exc}")

    def refresh_schedule_list(self):
        """Called by App when a scheduler notification arrives."""
        self._load_schedules()

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    def _save_settings(self):
        self._settings.set("log_level",  self._log_level_var.get())
        self._settings.set("theme",      self._theme_var.get())
        self._settings.set("export_dir", self._export_dir_var.get())

    def _reset_to_defaults(self):
        self._settings.reset_to_defaults()
        self._log_level_var.set(self._settings.get("log_level", "INFO"))
        self._theme_var.set(self._settings.get("theme", "dark"))
        self._export_dir_var.set(self._settings.get("export_dir", "exports/"))
        ctk.set_appearance_mode(self._settings.get("theme", "dark"))

    def _add_schedule_dialog(self):
        """Minimal Add Schedule dialog."""
        dialog = ctk.CTkToplevel(self)
        dialog.title("Add Schedule")
        dialog.geometry("400x280")
        dialog.grab_set()

        fields = {}
        for i, (label, default, values) in enumerate([
            ("Report Type", "INVENTORY", ["INVENTORY", "FORECAST", "POLICY", "EXECUTIVE"]),
            ("Format",      "PDF",       ["PDF", "EXCEL"]),
        ]):
            ctk.CTkLabel(dialog, text=label, font=FONT_SMALL).grid(row=i, column=0, padx=12, pady=6, sticky="w")
            var = ctk.StringVar(value=default)
            ctk.CTkOptionMenu(dialog, variable=var, values=values, width=200).grid(row=i, column=1, padx=12, pady=6)
            fields[label] = var

        ctk.CTkLabel(dialog, text="Cron (5-field)", font=FONT_SMALL).grid(row=2, column=0, padx=12, pady=6, sticky="w")
        cron_entry = ctk.CTkEntry(dialog, width=200)
        cron_entry.insert(0, "0 8 * * 1")
        cron_entry.grid(row=2, column=1, padx=12, pady=6)

        ctk.CTkLabel(dialog, text="Output Dir", font=FONT_SMALL).grid(row=3, column=0, padx=12, pady=6, sticky="w")
        dir_entry = ctk.CTkEntry(dialog, width=200)
        dir_entry.insert(0, "exports/")
        dir_entry.grid(row=3, column=1, padx=12, pady=6)

        err_label = ctk.CTkLabel(dialog, text="", text_color=COLOR_DANGER, font=FONT_SMALL)
        err_label.grid(row=4, column=0, columnspan=2, padx=12)

        def _submit():
            if not self._scheduler:
                dialog.destroy()
                return
            try:
                user = AuthService.get_current_user()
                self._scheduler.create_schedule(
                    report_type=fields["Report Type"].get(),
                    export_format=fields["Format"].get(),
                    cron_expression=cron_entry.get().strip(),
                    output_dir=dir_entry.get().strip(),
                    created_by=user.username if user else "admin",
                )
                dialog.destroy()
                self._load_schedules()
            except ValueError as exc:
                err_label.configure(text=str(exc))

        ctk.CTkButton(dialog, text="Create", command=_submit).grid(
            row=5, column=0, columnspan=2, pady=10
        )

    def _deactivate_selected_schedule(self):
        if not hasattr(self, "_schedule_table") or not self._scheduler:
            return
        selected = getattr(self._schedule_table, "_selected_row", None)
        if selected:
            self.logger.warning("Schedule deactivation requires row selection — not yet wired.")

    def _add_user_dialog(self):
        """Minimal Add User dialog."""
        from src.services.auth_service import AuthService
        dialog = ctk.CTkToplevel(self)
        dialog.title("Add User")
        dialog.geometry("360x240")
        dialog.grab_set()

        ctk.CTkLabel(dialog, text="Username", font=FONT_SMALL).grid(row=0, column=0, padx=12, pady=6, sticky="w")
        u_entry = ctk.CTkEntry(dialog, width=180)
        u_entry.grid(row=0, column=1, padx=12, pady=6)

        ctk.CTkLabel(dialog, text="Password", font=FONT_SMALL).grid(row=1, column=0, padx=12, pady=6, sticky="w")
        p_entry = ctk.CTkEntry(dialog, width=180, show="•")
        p_entry.grid(row=1, column=1, padx=12, pady=6)

        ctk.CTkLabel(dialog, text="Role", font=FONT_SMALL).grid(row=2, column=0, padx=12, pady=6, sticky="w")
        role_var = ctk.StringVar(value="VIEWER")
        ctk.CTkOptionMenu(dialog, variable=role_var, values=["ADMIN", "BUYER", "VIEWER"], width=180).grid(row=2, column=1, padx=12, pady=6)

        err_label = ctk.CTkLabel(dialog, text="", text_color=COLOR_DANGER, font=FONT_SMALL)
        err_label.grid(row=3, column=0, columnspan=2)

        def _submit():
            try:
                auth = AuthService()
                hashed = auth.hash_password(p_entry.get())
                self._user_repo.create(username=u_entry.get().strip(), hashed_password=hashed, role=role_var.get())
                dialog.destroy()
                self._load_users()
            except Exception as exc:
                err_label.configure(text=str(exc)[:60])

        ctk.CTkButton(dialog, text="Create User", command=_submit).grid(row=4, column=0, columnspan=2, pady=10)

    def _deactivate_selected_user(self):
        self.logger.warning("User deactivation requires row selection — not yet wired.")

    def mark_stale(self):
        self._stale = True

    def update_language(self):
        pass
