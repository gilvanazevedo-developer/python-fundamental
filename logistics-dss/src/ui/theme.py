"""
UI Theme Configuration
Centralized style constants for consistent appearance.
"""

# Color Palette
COLOR_PRIMARY = "#1f6aa5"
COLOR_SUCCESS = "#2fa572"
COLOR_WARNING = "#e8a838"
COLOR_DANGER = "#d64545"
COLOR_NEUTRAL = "#6b7280"

# Background colors per mode
COLOR_BG_CARD_DARK = "#2b2b2b"
COLOR_BG_CARD_LIGHT = "#ffffff"
COLOR_BG_SIDEBAR_DARK = "#1a1a2e"
COLOR_BG_SIDEBAR_LIGHT = "#e8e8e8"
COLOR_TEXT_DARK = "#dce4ee"
COLOR_TEXT_LIGHT = "#1a1a1a"

# Fonts
FONT_HEADER = ("Segoe UI", 18, "bold")
FONT_SUBHEADER = ("Segoe UI", 14, "bold")
FONT_KPI_VALUE = ("Segoe UI", 26, "bold")
FONT_KPI_LABEL = ("Segoe UI", 11)
FONT_TABLE = ("Consolas", 11)
FONT_TABLE_HEADER = ("Segoe UI", 11, "bold")
FONT_BODY = ("Segoe UI", 12)
FONT_SMALL = ("Segoe UI", 10)
FONT_NAV = ("Segoe UI", 13)
FONT_NAV_ACTIVE = ("Segoe UI", 13, "bold")
FONT_STATUS = ("Segoe UI", 10)

# Card styling
CARD_CORNER_RADIUS = 10
CARD_PADDING = 15
CARD_HEIGHT = 100

# Spacing
SECTION_PADDING = 15
COMPONENT_GAP = 10

# Table
TABLE_ROW_HEIGHT = 28
TABLE_HEADER_HEIGHT = 30


def format_number(value, decimals=0):
    """Format a number with thousands separator."""
    if value is None:
        return "N/A"
    if decimals == 0:
        return f"{int(value):,}"
    return f"{value:,.{decimals}f}"


def format_currency(value):
    """Format a number as currency."""
    if value is None:
        return "N/A"
    if abs(value) >= 1_000_000:
        return f"${value / 1_000_000:,.1f}M"
    if abs(value) >= 1_000:
        return f"${value / 1_000:,.1f}K"
    return f"${value:,.2f}"


def format_percentage(value):
    """Format a number as percentage."""
    if value is None:
        return "N/A"
    return f"{value:.1f}%"
