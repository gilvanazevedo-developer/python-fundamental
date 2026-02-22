"""
Audit Log View
Paginated audit trail table with event-type filter and actor search.
Accessible to ADMIN role only — BUYER and VIEWER see an access-denied message.
"""

import sys
from pathlib import Path

import customtkinter as ctk

PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.services.audit_service import AuditService
from src.services.auth_service import AuthService
from src.ui.components.data_table import DataTable
from src.ui.theme import (
    COLOR_DANGER,
    COLOR_NEUTRAL,
    FONT_SUBHEADER,
    FONT_SMALL,
    SECTION_PADDING,
)
from src.i18n import t
from src.logger import LoggerMixin
from config.constants import ROLE_ADMIN

_EVENT_TYPES = [
    "All", "LOGIN", "LOGOUT",
    "OPTIMIZATION_RUN", "IMPORT_COMPLETED",
    "SCHEDULE_RUN", "SETTINGS_CHANGED",
    "USER_CREATED", "USER_DEACTIVATED",
]


class AuditLogView(ctk.CTkFrame, LoggerMixin):
    """ADMIN-only paginated audit trail view."""

    def __init__(self, master, current_user=None, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self._audit = AuditService()
        self._current_user = current_user
        self._stale = True
        self._build()

    # ------------------------------------------------------------------
    # Layout
    # ------------------------------------------------------------------

    def _build(self):
        user = self._current_user or AuthService.get_current_user()
        is_admin = user and user.role == ROLE_ADMIN

        if not is_admin:
            # Access-denied message for non-ADMIN roles
            ctk.CTkLabel(
                self,
                text="Access Denied — Administrator role required.",
                font=FONT_SUBHEADER,
                text_color=COLOR_DANGER,
            ).pack(expand=True)
            return

        # Admin layout
        self._scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self._scroll.pack(fill="both", expand=True)

        # Header
        ctk.CTkLabel(
            self._scroll, text="Audit Log", font=FONT_SUBHEADER, anchor="w"
        ).pack(fill="x", padx=SECTION_PADDING, pady=(SECTION_PADDING, 6))

        # Controls
        controls = ctk.CTkFrame(self._scroll, fg_color="transparent")
        controls.pack(fill="x", padx=SECTION_PADDING, pady=(0, 8))

        ctk.CTkLabel(controls, text="Event Type:", font=FONT_SMALL).grid(
            row=0, column=0, padx=(0, 4), sticky="w"
        )
        self._type_var = ctk.StringVar(value="All")
        ctk.CTkOptionMenu(
            controls, variable=self._type_var,
            values=_EVENT_TYPES, width=160, height=28,
            command=self._on_filter_change,
        ).grid(row=0, column=1, padx=(0, 12), sticky="w")

        ctk.CTkLabel(controls, text="Actor:", font=FONT_SMALL).grid(
            row=0, column=2, padx=(0, 4), sticky="w"
        )
        self._actor_var = ctk.StringVar()
        ctk.CTkEntry(
            controls, textvariable=self._actor_var, width=120, height=28,
        ).grid(row=0, column=3, padx=(0, 8), sticky="w")

        ctk.CTkButton(
            controls, text="Search", width=80, height=28, command=self._reload
        ).grid(row=0, column=4, sticky="w")

        ctk.CTkLabel(
            controls,
            text="Showing 200 most recent events",
            font=FONT_SMALL,
            text_color=COLOR_NEUTRAL,
        ).grid(row=0, column=5, padx=(16, 0), sticky="w")

        # Table
        self._table = DataTable(
            self._scroll,
            columns=[
                {"key": "occurred_at", "label": "Timestamp",  "width": 160},
                {"key": "event_type",  "label": "Event Type", "width": 180},
                {"key": "actor",       "label": "Actor",      "width": 120},
                {"key": "entity_type", "label": "Entity",     "width": 120},
                {"key": "detail",      "label": "Detail",     "width": 280},
            ],
            height=20,
        )
        self._table.pack(
            fill="both", padx=SECTION_PADDING, pady=(0, SECTION_PADDING), expand=True
        )

    # ------------------------------------------------------------------
    # Data
    # ------------------------------------------------------------------

    def refresh(self):
        if not self._stale:
            return
        self._stale = False
        self._reload()

    def _on_filter_change(self, _value=None):
        self._reload()

    def _reload(self):
        user = self._current_user or AuthService.get_current_user()
        if not user or user.role != ROLE_ADMIN:
            return

        try:
            events = self._audit.get_recent_events(limit=200)
            actor_filter = self._actor_var.get().strip().lower()
            type_filter = self._type_var.get()

            if type_filter != "All":
                events = [e for e in events if e["event_type"] == type_filter]
            if actor_filter:
                events = [e for e in events if actor_filter in e["actor"].lower()]

            rows = []
            for e in events:
                detail_str = ""
                if isinstance(e.get("detail"), dict):
                    detail_str = ", ".join(f"{k}={v}" for k, v in e["detail"].items())
                elif e.get("detail"):
                    detail_str = str(e["detail"])

                rows.append({
                    "occurred_at": (e["occurred_at"] or "")[:19].replace("T", " "),
                    "event_type":  e["event_type"],
                    "actor":       e["actor"],
                    "entity_type": e.get("entity_type") or "",
                    "detail":      detail_str,
                })

            self._table.load_data(rows)
        except Exception as exc:
            self.logger.error(f"Audit log reload failed: {exc}")

    def mark_stale(self):
        self._stale = True

    def update_language(self):
        pass  # Column labels are English-only for audit log
