"""
Login View
Presents credential form, first-run banner, and lockout feedback.
On successful login calls on_success(user) to hand off to the main App.
"""

import sys
from pathlib import Path
from typing import Callable, Optional

import customtkinter as ctk

PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.services.auth_service import AuthService, LockedAccountError
from src.repositories.user_repository import UserRepository
from src.ui.theme import (
    COLOR_PRIMARY,
    COLOR_DANGER,
    COLOR_WARNING,
    FONT_HEADER,
    FONT_BODY,
    FONT_SMALL,
    FONT_SUBHEADER,
)
from src.logger import LoggerMixin


class LoginView(ctk.CTk, LoggerMixin):
    """Standalone login window — shown before the main App."""

    def __init__(self, on_success: Callable):
        super().__init__()

        self._on_success = on_success
        self._auth = AuthService()
        self._user_repo = UserRepository()

        self.title("Logistics DSS — Login")
        self.geometry("420x460")
        self.resizable(False, False)

        self._build()
        self._check_first_run()

    # ------------------------------------------------------------------
    # Layout
    # ------------------------------------------------------------------

    def _build(self):
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        frame = ctk.CTkFrame(self, corner_radius=12)
        frame.grid(row=0, column=0, padx=40, pady=40, sticky="nsew")
        frame.grid_rowconfigure((0, 1, 2, 3, 4, 5, 6, 7), weight=0)
        frame.grid_columnconfigure(0, weight=1)

        # App title
        ctk.CTkLabel(
            frame, text="Logistics DSS", font=FONT_HEADER, text_color=COLOR_PRIMARY
        ).grid(row=0, column=0, pady=(30, 4))

        ctk.CTkLabel(
            frame, text="Decision Support System", font=FONT_SMALL
        ).grid(row=1, column=0, pady=(0, 20))

        # First-run / lockout banner (hidden by default)
        self._banner = ctk.CTkLabel(
            frame, text="", font=FONT_SMALL,
            text_color="white",
            fg_color=COLOR_WARNING,
            corner_radius=6,
            wraplength=280,
        )
        # Not packed initially — shown only when needed

        # Username
        ctk.CTkLabel(frame, text="Username", font=FONT_SMALL, anchor="w").grid(
            row=3, column=0, padx=30, sticky="w"
        )
        self._username_entry = ctk.CTkEntry(frame, width=280, height=34)
        self._username_entry.grid(row=4, column=0, padx=30, pady=(2, 10))
        self._username_entry.focus()

        # Password
        ctk.CTkLabel(frame, text="Password", font=FONT_SMALL, anchor="w").grid(
            row=5, column=0, padx=30, sticky="w"
        )
        self._password_entry = ctk.CTkEntry(frame, width=280, height=34, show="•")
        self._password_entry.grid(row=6, column=0, padx=30, pady=(2, 16))
        self._password_entry.bind("<Return>", lambda _e: self._attempt_login())

        # Login button
        self._login_btn = ctk.CTkButton(
            frame, text="Log In", width=280, height=36, command=self._attempt_login
        )
        self._login_btn.grid(row=7, column=0, padx=30, pady=(0, 10))

        # Error label (hidden by default)
        self._error_label = ctk.CTkLabel(
            frame, text="", font=FONT_SMALL, text_color=COLOR_DANGER
        )
        self._error_label.grid(row=8, column=0, pady=(0, 20))

    # ------------------------------------------------------------------
    # First-run
    # ------------------------------------------------------------------

    def _check_first_run(self):
        """Create the default admin if no users exist; show the first-run banner."""
        users = self._user_repo.get_all(active_only=False)
        if not users:
            self._auth.create_default_admin()
            self._show_banner(
                "Default admin account created.\n"
                "Username: admin   Password: admin123\n"
                "Change your password immediately!",
                color=COLOR_WARNING,
            )

    def _show_banner(self, text: str, color: str = COLOR_WARNING):
        self._banner.configure(text=text, fg_color=color)
        self._banner.grid(row=2, column=0, padx=30, pady=(0, 10), sticky="ew")

    # ------------------------------------------------------------------
    # Authentication
    # ------------------------------------------------------------------

    def _attempt_login(self):
        username = self._username_entry.get().strip()
        password = self._password_entry.get()

        if not username:
            self._error_label.configure(text="Please enter your username.")
            return

        self._error_label.configure(text="")
        self._login_btn.configure(state="disabled", text="Authenticating…")
        self.update_idletasks()

        try:
            user = self._auth.authenticate(username, password)
            if user:
                self.logger.info(f"Successful login: {username} ({user.role})")
                self.destroy()
                self._on_success(user)
            else:
                self._login_btn.configure(state="normal", text="Log In")
                self._error_label.configure(text="Invalid username or password.")
        except LockedAccountError:
            self._login_btn.configure(state="disabled", text="Log In")
            self._error_label.configure(
                text="Account locked. Contact your administrator."
            )
        except Exception as exc:
            self.logger.error(f"Login error: {exc}")
            self._login_btn.configure(state="normal", text="Log In")
            self._error_label.configure(text="An error occurred. Please try again.")
