"""
KPI Card Widget
Displays a single KPI metric with label, value, and optional trend.
"""

import customtkinter as ctk

from src.ui.theme import (
    COLOR_PRIMARY,
    COLOR_SUCCESS,
    COLOR_WARNING,
    COLOR_DANGER,
    COLOR_NEUTRAL,
    FONT_KPI_VALUE,
    FONT_KPI_LABEL,
    FONT_SMALL,
    CARD_CORNER_RADIUS,
    CARD_PADDING,
)


class KPICard(ctk.CTkFrame):
    """A card widget displaying a single KPI metric."""

    def __init__(
        self,
        master,
        label: str = "",
        value: str = "0",
        color: str = None,
        **kwargs,
    ):
        super().__init__(
            master,
            corner_radius=CARD_CORNER_RADIUS,
            **kwargs,
        )

        self._label_text = label
        self._value_text = value
        self._color = color or COLOR_PRIMARY

        # Label
        self._label = ctk.CTkLabel(
            self,
            text=label,
            font=FONT_KPI_LABEL,
            text_color=COLOR_NEUTRAL,
            anchor="w",
        )
        self._label.pack(
            fill="x", padx=CARD_PADDING, pady=(CARD_PADDING, 2)
        )

        # Value
        self._value_label = ctk.CTkLabel(
            self,
            text=value,
            font=FONT_KPI_VALUE,
            text_color=self._color,
            anchor="w",
        )
        self._value_label.pack(
            fill="x", padx=CARD_PADDING, pady=(0, 2)
        )

        # Trend (optional, hidden initially)
        self._trend_label = ctk.CTkLabel(
            self,
            text="",
            font=FONT_SMALL,
            text_color=COLOR_NEUTRAL,
            anchor="w",
        )
        self._trend_label.pack(
            fill="x", padx=CARD_PADDING, pady=(0, CARD_PADDING)
        )

    def set_label(self, text: str) -> None:
        """Update the label text (used by i18n language switching)."""
        self._label.configure(text=text)

    def update(self, value: str, trend: str = "", color: str = None):
        """Update the displayed value and optional trend."""
        self._value_label.configure(text=value)
        if color:
            self._color = color
            self._value_label.configure(text_color=color)
        if trend:
            self._trend_label.configure(text=trend)
        else:
            self._trend_label.configure(text="")
