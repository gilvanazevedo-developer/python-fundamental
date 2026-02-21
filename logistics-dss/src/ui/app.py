"""
Main Application Window
Root window with navigation sidebar and view management.
"""

import sys
from pathlib import Path

import customtkinter as ctk

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from config import settings
from src.database.connection import get_db_manager
from src.i18n import t, set_language, get_language
from src.ui.theme import (
    COLOR_PRIMARY,
    COLOR_BG_SIDEBAR_DARK,
    COLOR_BG_SIDEBAR_LIGHT,
    FONT_HEADER,
    FONT_NAV,
    FONT_NAV_ACTIVE,
    FONT_STATUS,
    SECTION_PADDING,
)
from src.ui.views.dashboard_view import DashboardView
from src.ui.views.inventory_view import InventoryView
from src.ui.views.import_view import ImportView
from src.ui.views.analytics_view import AnalyticsView
from src.ui.views.forecast_view import ForecastView
from src.ui.views.optimization_view import OptimizationView
from src.ui.views.executive_view import ExecutiveView
from src.ui.components.status_bar import StatusBar
from src.logger import LoggerMixin


class LogisticsDSSApp(ctk.CTk, LoggerMixin):
    """Main application window."""

    def __init__(self):
        super().__init__()

        # Configure window
        self.title(settings.WINDOW_TITLE)
        self.geometry(f"{settings.WINDOW_WIDTH}x{settings.WINDOW_HEIGHT}")
        self.minsize(settings.WINDOW_MIN_WIDTH, settings.WINDOW_MIN_HEIGHT)

        ctk.set_appearance_mode(settings.APPEARANCE_MODE)
        ctk.set_default_color_theme(settings.COLOR_THEME)

        # Initialize database
        self._init_database()

        # State
        self._current_view_name = None
        self._views = {}
        self._nav_buttons = {}

        # Build UI
        self._build_layout()
        self._build_sidebar()
        self._build_views()
        self._build_status_bar()

        # Show default view
        self._switch_view("executive")

        self.logger.info("Application started")

    def _init_database(self):
        """Initialize the database and create tables if needed."""
        try:
            db_manager = get_db_manager()
            db_manager.create_tables()
            self.logger.info("Database initialized")
        except Exception as e:
            self.logger.error(f"Database initialization failed: {e}")

    def _build_layout(self):
        """Create the main layout grid."""
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)

    def _build_sidebar(self):
        """Build the navigation sidebar."""
        self._sidebar = ctk.CTkFrame(
            self, width=settings.NAV_WIDTH, corner_radius=0
        )
        self._sidebar.grid(row=0, column=0, sticky="nsw")
        self._sidebar.grid_propagate(False)

        # App title
        title_label = ctk.CTkLabel(
            self._sidebar,
            text="Logistics\nDSS",
            font=FONT_HEADER,
            text_color=COLOR_PRIMARY,
        )
        title_label.pack(pady=(25, 30), padx=10)

        # Navigation buttons
        nav_items = [
            ("executive",    "nav.executive"),
            ("dashboard",    "nav.dashboard"),
            ("inventory",    "nav.inventory"),
            ("analytics",    "nav.analytics"),
            ("forecasting",  "nav.forecasting"),
            ("optimization", "nav.optimization"),
            ("import",       "nav.import"),
        ]
        self._nav_label_keys = {v: k for v, k in nav_items}

        for view_name, lbl_key in nav_items:
            btn = ctk.CTkButton(
                self._sidebar,
                text=t(lbl_key),
                font=FONT_NAV,
                height=40,
                corner_radius=8,
                fg_color="transparent",
                text_color=("gray10", "gray90"),
                hover_color=("gray75", "gray30"),
                anchor="w",
                command=lambda v=view_name: self._switch_view(v),
            )
            btn.pack(fill="x", padx=10, pady=3)
            self._nav_buttons[view_name] = btn

        # Appearance mode toggle at bottom
        self._sidebar.pack_propagate(False)

        # Language selector (above appearance)
        lang_frame = ctk.CTkFrame(self._sidebar, fg_color="transparent")
        lang_frame.pack(side="bottom", fill="x", padx=10, pady=(0, 5))

        self._lbl_language = ctk.CTkLabel(lang_frame, text=t("app.language"), font=FONT_STATUS)
        self._lbl_language.pack(anchor="w")

        _lang_display = {"en": "English", "pt": "Português", "es": "Español"}
        self._lang_menu = ctk.CTkOptionMenu(
            lang_frame,
            values=["English", "Português", "Español"],
            command=self._change_language,
            width=140,
            height=28,
        )
        self._lang_menu.set(_lang_display.get(settings.DEFAULT_LANGUAGE, "English"))
        self._lang_menu.pack(fill="x", pady=(3, 0))

        mode_frame = ctk.CTkFrame(self._sidebar, fg_color="transparent")
        mode_frame.pack(side="bottom", fill="x", padx=10, pady=(0, 5))

        self._lbl_appearance = ctk.CTkLabel(mode_frame, text=t("app.appearance"), font=FONT_STATUS)
        self._lbl_appearance.pack(anchor="w")

        self._mode_menu = ctk.CTkOptionMenu(
            mode_frame,
            values=["Dark", "Light", "System"],
            command=self._change_appearance,
            width=140,
            height=28,
        )
        self._mode_menu.set(settings.APPEARANCE_MODE.capitalize())
        self._mode_menu.pack(fill="x", pady=(3, 0))

    def _build_views(self):
        """Create all view frames (hidden initially)."""
        self._content_frame = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        self._content_frame.grid(row=0, column=1, sticky="nsew")
        self._content_frame.grid_rowconfigure(0, weight=1)
        self._content_frame.grid_columnconfigure(0, weight=1)

        self._views["executive"]    = ExecutiveView(self._content_frame)
        self._views["dashboard"]    = DashboardView(self._content_frame)
        self._views["inventory"]    = InventoryView(self._content_frame)
        self._views["analytics"]    = AnalyticsView(self._content_frame)
        self._views["forecasting"]  = ForecastView(self._content_frame)
        self._views["optimization"] = OptimizationView(self._content_frame)
        self._views["import"]       = ImportView(
            self._content_frame, on_import_complete=self._on_import_complete
        )

        for view in self._views.values():
            view.grid(row=0, column=0, sticky="nsew")

    def _build_status_bar(self):
        """Build the bottom status bar."""
        self._status_bar = StatusBar(self)
        self._status_bar.grid(row=1, column=0, columnspan=2, sticky="ew")
        self._status_bar.refresh()

    def _switch_view(self, view_name: str):
        """Switch the active view."""
        if view_name == self._current_view_name:
            return

        # Update nav button styles
        for name, btn in self._nav_buttons.items():
            if name == view_name:
                btn.configure(fg_color=COLOR_PRIMARY, font=FONT_NAV_ACTIVE)
            else:
                btn.configure(fg_color="transparent", font=FONT_NAV)

        # Raise the selected view
        view = self._views.get(view_name)
        if view:
            view.tkraise()
            view.refresh()

        self._current_view_name = view_name
        self.logger.debug(f"Switched to view: {view_name}")

    def _change_appearance(self, mode: str):
        """Change appearance mode."""
        ctk.set_appearance_mode(mode.lower())

    def _change_language(self, choice: str):
        """Switch the active UI language and refresh all views."""
        lang_map = {"English": "en", "Português": "pt", "Español": "es"}
        set_language(lang_map.get(choice, "en"))

        # Update sidebar labels
        self._lbl_appearance.configure(text=t("app.appearance"))
        self._lbl_language.configure(text=t("app.language"))

        # Update nav buttons (restore transparent style first)
        for view_name, btn in self._nav_buttons.items():
            lbl_key = self._nav_label_keys.get(view_name, view_name)
            if view_name == self._current_view_name:
                btn.configure(text=t(lbl_key), fg_color=COLOR_PRIMARY, font=FONT_NAV_ACTIVE)
            else:
                btn.configure(text=t(lbl_key), fg_color="transparent", font=FONT_NAV)

        # Delegate to views that support language switching
        for view in self._views.values():
            if hasattr(view, "update_language"):
                view.update_language()

        self.logger.debug(f"Language changed to: {get_language()}")

    def _on_import_complete(self):
        """Called after a successful import to refresh other views."""
        self._status_bar.refresh()
        # Mark data views for refresh on next switch
        dashboard = self._views.get("dashboard")
        if dashboard:
            dashboard.mark_stale()
        inventory = self._views.get("inventory")
        if inventory:
            inventory.mark_stale()
        analytics = self._views.get("analytics")
        if analytics:
            analytics.mark_stale()
        forecasting = self._views.get("forecasting")
        if forecasting:
            forecasting.mark_stale()
        optimization = self._views.get("optimization")
        if optimization:
            optimization.mark_stale()
        executive = self._views.get("executive")
        if executive:
            executive.mark_stale()
