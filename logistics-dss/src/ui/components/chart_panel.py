"""
Chart Panel Widget
Matplotlib figure embedded in CustomTkinter.
"""

import customtkinter as ctk
import matplotlib
matplotlib.use("TkAgg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
from typing import List, Optional

from src.ui.theme import COLOR_PRIMARY, COLOR_SUCCESS, COLOR_WARNING, COLOR_NEUTRAL


class ChartPanel(ctk.CTkFrame):
    """Embeds a Matplotlib chart inside a CustomTkinter frame."""

    def __init__(self, master, figsize=(5, 3), **kwargs):
        super().__init__(master, **kwargs)

        self._figsize = figsize
        self._figure = Figure(figsize=figsize, dpi=100)
        self._figure.patch.set_alpha(0)
        self._ax = self._figure.add_subplot(111)

        self._mpl_canvas = FigureCanvasTkAgg(self._figure, self)
        self._mpl_canvas.get_tk_widget().pack(fill="both", expand=True, padx=5, pady=5)

    def _style_axis(self, title: str = ""):
        """Apply consistent styling to the axes."""
        mode = ctk.get_appearance_mode()
        if mode == "Dark":
            text_color = "#dce4ee"
            grid_color = "#3a3a3a"
            bg_color = "#2b2b2b"
        else:
            text_color = "#1a1a1a"
            grid_color = "#e0e0e0"
            bg_color = "#ffffff"

        self._ax.set_facecolor(bg_color)
        self._figure.patch.set_facecolor(bg_color)
        self._ax.set_title(title, color=text_color, fontsize=11, fontweight="bold", pad=10)
        self._ax.tick_params(colors=text_color, labelsize=9)
        for spine in self._ax.spines.values():
            spine.set_color(grid_color)
        self._ax.yaxis.grid(True, color=grid_color, alpha=0.5, linestyle="--")
        self._ax.set_axisbelow(True)

    def plot_bar(
        self,
        labels: List[str],
        values: List[float],
        title: str = "",
        color: str = None,
    ):
        """Render a vertical bar chart."""
        self._ax.clear()
        if not labels:
            self._style_axis(title)
            self._ax.text(0.5, 0.5, "No data", ha="center", va="center",
                         transform=self._ax.transAxes, color=COLOR_NEUTRAL)
            self._mpl_canvas.draw_idle()
            return

        bar_color = color or COLOR_PRIMARY
        bars = self._ax.bar(labels, values, color=bar_color, width=0.6, zorder=3)

        # Rotate labels if many
        if len(labels) > 5:
            self._ax.tick_params(axis="x", rotation=45)
            self._figure.subplots_adjust(bottom=0.25)
        else:
            self._figure.subplots_adjust(bottom=0.15)

        self._style_axis(title)
        self._figure.tight_layout()
        self._mpl_canvas.draw_idle()

    def plot_line(
        self,
        x: List,
        y: List[float],
        title: str = "",
        xlabel: str = "",
        ylabel: str = "",
        color: str = None,
    ):
        """Render a line chart."""
        self._ax.clear()
        if not x:
            self._style_axis(title)
            self._ax.text(0.5, 0.5, "No data", ha="center", va="center",
                         transform=self._ax.transAxes, color=COLOR_NEUTRAL)
            self._mpl_canvas.draw_idle()
            return

        line_color = color or COLOR_SUCCESS
        self._ax.plot(x, y, color=line_color, linewidth=2, marker="o", markersize=4, zorder=3)
        self._ax.fill_between(x, y, alpha=0.1, color=line_color)

        if xlabel:
            mode = ctk.get_appearance_mode()
            lbl_color = "#dce4ee" if mode == "Dark" else "#1a1a1a"
            self._ax.set_xlabel(xlabel, color=lbl_color, fontsize=9)
        if ylabel:
            mode = ctk.get_appearance_mode()
            lbl_color = "#dce4ee" if mode == "Dark" else "#1a1a1a"
            self._ax.set_ylabel(ylabel, color=lbl_color, fontsize=9)

        # Rotate date labels
        if len(x) > 7:
            self._ax.tick_params(axis="x", rotation=45)
            self._figure.subplots_adjust(bottom=0.25)
        else:
            self._figure.subplots_adjust(bottom=0.15)

        self._style_axis(title)
        self._figure.tight_layout()
        self._mpl_canvas.draw_idle()

    def plot_horizontal_bar(
        self,
        labels: List[str],
        values: List[float],
        title: str = "",
        color: str = None,
    ):
        """Render a horizontal bar chart."""
        self._ax.clear()
        if not labels:
            self._style_axis(title)
            self._ax.text(0.5, 0.5, "No data", ha="center", va="center",
                         transform=self._ax.transAxes, color=COLOR_NEUTRAL)
            self._mpl_canvas.draw_idle()
            return

        bar_color = color or COLOR_PRIMARY
        self._ax.barh(labels, values, color=bar_color, height=0.5, zorder=3)
        self._ax.invert_yaxis()

        self._style_axis(title)
        self._figure.tight_layout()
        self._mpl_canvas.draw_idle()

    def clear(self):
        """Clear the current plot."""
        self._ax.clear()
        self._mpl_canvas.draw_idle()

    def refresh(self):
        """Redraw the canvas."""
        self._mpl_canvas.draw_idle()
