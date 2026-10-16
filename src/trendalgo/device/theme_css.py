"""Color rules and the stylesheet for the device app. Pure: no Qt import, so the rules are testable.

Every color comes from `design_tokens` (the Golden Path tokens). Nothing in this file holds a raw
hex value. The stylesheet follows the Golden Path web look: panels on the surface color, one primary action
on the primary container, and the active section on the primary container.
"""

from __future__ import annotations

from string import Template
from typing import Literal

from trendalgo.device import design_tokens as T

Mode = Literal["light", "dark"]
PX_TO_PT = 0.75  # 96 dpi: 1 pt = 4/3 px

_STYLE = Template(
    """
QMainWindow, QDialog { background: ${background}; color: ${onBackground}; }
QLabel { color: ${onBackground}; background: transparent; }
QLabel#pageTitle, QLabel#brandName { font-size: ${title_pt}pt; font-weight: 600; color: ${onSurface}; }
QLabel#status, QLabel#subtitle, QLabel#hint { color: ${onSurfaceVariant}; }
QLabel#sectionTitle, QLabel#emptyTitle { font-weight: 600; color: ${onSurface}; }
QLabel#problem { font-weight: 600; color: ${error}; }
QLabel#badge { background: ${secondaryContainer}; color: ${onSecondaryContainer};
    border-radius: ${radius_sm}px; padding: 3px ${space_sm}px; font-weight: 600; }
QFrame#emptyState, QFrame#panel { background: ${surface}; border: 1px solid ${outline};
    border-radius: ${radius_md}px; padding: ${space_md}px; }
QWidget#navRow { border-bottom: 1px solid ${outline}; }
QTabBar { background: transparent; }
QTabBar::tab { background: transparent; color: ${onSurfaceVariant}; border: none;
    border-bottom: 2px solid transparent; border-radius: ${radius_md}px;
    padding: 8px ${space_md}px; margin: 0 2px; }
QTabBar::tab:hover:!selected { background: ${surfaceVariant}; color: ${onSurface}; }
QTabBar::tab:selected { background: ${primaryContainer}; color: ${onPrimaryContainer};
    border-bottom: 2px solid ${primary}; font-weight: 600; }
QPushButton { background: ${surfaceVariant}; color: ${onSurfaceVariant};
    border: 1px solid ${outline}; border-radius: ${radius_md}px;
    padding: ${space_sm}px ${space_md}px; min-height: 22px; }
QPushButton:hover { color: ${onSurface}; }
QPushButton:focus { border: 2px solid ${primary}; }
QPushButton:disabled { color: ${outline}; background: ${surface}; }
QPushButton[role="primary"] { background: ${primaryContainer}; color: ${onPrimaryContainer};
    border: 1px solid ${primary}; font-weight: 600; }
QPushButton[role="primary"]:focus { border: 2px solid ${primary}; }
QPushButton[role="primary"]:disabled { color: ${outline}; background: ${surface};
    border: 1px solid ${outline}; }
QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox { background: ${background};
    color: ${onBackground}; border: 1px solid ${outline}; border-radius: ${radius_sm}px;
    padding: 6px ${space_sm}px; min-height: 22px; selection-background-color: ${primaryContainer};
    selection-color: ${onPrimaryContainer}; }
QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus {
    border: 2px solid ${primary}; padding: 5px 7px; }
QLineEdit:disabled, QComboBox:disabled, QSpinBox:disabled, QDoubleSpinBox:disabled {
    color: ${outline}; background: ${surface}; }
QComboBox QAbstractItemView { background: ${background}; color: ${onBackground};
    border: 1px solid ${outline}; selection-background-color: ${primaryContainer};
    selection-color: ${onPrimaryContainer}; }
QTableWidget, QTableView { background: ${background}; alternate-background-color: ${surface};
    color: ${onBackground}; gridline-color: ${surfaceVariant}; border: 1px solid ${outline};
    border-radius: ${radius_md}px; selection-background-color: ${primaryContainer};
    selection-color: ${onPrimaryContainer}; }
QHeaderView::section { background: ${surfaceVariant}; color: ${onSurfaceVariant}; border: none;
    border-bottom: 1px solid ${outline}; padding: 6px ${space_sm}px; font-weight: 600; }
QTableCornerButton::section { background: ${surfaceVariant}; border: none; }
QStatusBar { background: ${surface}; color: ${onSurfaceVariant};
    border-top: 1px solid ${outline}; }
QStatusBar QLabel { color: ${onSurfaceVariant}; }
QToolTip { background: ${surface}; color: ${onSurface}; border: 1px solid ${outline};
    padding: 4px 6px; }
QFrame#kpiStrip { background: transparent; border: none; }
QFrame#kpiCard { background: ${surfaceVariant}; border: 1px solid ${outline};
    border-radius: ${radius_md}px; }
QLabel#kpiTitle { color: ${onSurfaceVariant}; font-size: 10pt; font-weight: 600; }
QLabel#kpiValue { color: ${onSurface}; font-size: ${title_pt}pt; font-weight: 700; }
QFrame#compareBar { background: ${surface}; border: 1px solid ${outline};
    border-radius: ${radius_sm}px; }
QLabel#badgeNew { background: ${secondary}; color: ${onSecondary}; border-radius: 4px;
    padding: 1px 4px; font-size: 8pt; font-weight: 700; }
QLabel#exchangeChip { background: ${surfaceVariant}; color: ${onSurface};
    border-radius: ${radius_sm}px; padding: 2px 8px; }
QWidget#scannerFilterCell { background: ${surfaceVariant}; }
QWidget#scannerFilterCell QLineEdit, QWidget#scannerFilterCell QComboBox {
    min-height: 22px; max-height: 24px; padding: 0 2px; font-size: 9pt; }
QCheckBox { color: ${onSurface}; spacing: 6px; }
QCheckBox::indicator { width: 16px; height: 16px; border: 2px solid ${outline};
    border-radius: 3px; background: ${surface}; }
QCheckBox::indicator:unchecked { background: ${background}; border-color: ${outline}; }
QCheckBox::indicator:checked { background: ${primary}; border-color: ${primary}; }
QCheckBox::indicator:hover { border-color: ${primary}; }
"""
)


def resolve_mode(choice: str, system_is_dark: bool) -> Mode:
    """The mode to paint: an explicit light or dark choice wins; anything else follows the OS."""
    if choice == "light":
        return "light"
    if choice == "dark":
        return "dark"
    return "dark" if system_is_dark else "light"


def colors_for(mode: Mode, accent: str = "") -> dict[str, str]:
    """Token colors for one mode. An accent only replaces `primary`, and only a listed preset."""
    colors = dict(T.DARK if mode == "dark" else T.LIGHT)
    if accent in T.ACCENT_PRESETS:
        colors["primary"] = accent
    # Gain path colors from accent presets (not `secondary`, which is blue).
    colors["gainUp"] = T.ACCENT_PRESETS[1]
    colors["gainDown"] = colors["error"]
    return colors


def body_point_size() -> float:
    """The body text size in points, from the 14 px `bodyMedium` token."""
    return T.TEXT_SIZE_SP["bodyMedium"] * PX_TO_PT


def build_stylesheet(mode: Mode, accent: str = "") -> str:
    values: dict[str, str] = dict(colors_for(mode, accent))
    values.update(
        {
            "title_pt": _fmt(T.TEXT_SIZE_SP["titleLarge"] * PX_TO_PT),
            "radius_sm": str(T.RADIUS["sm"]),
            "radius_md": str(T.RADIUS["md"]),
            "space_sm": str(T.SPACING["sm"]),
            "space_md": str(T.SPACING["md"]),
        }
    )
    return _STYLE.substitute(values).strip()


def contrast_ratio(foreground: str, background: str) -> float:
    """WCAG contrast ratio between two `#RRGGBB` colors."""
    lighter = max(_luminance(foreground), _luminance(background))
    darker = min(_luminance(foreground), _luminance(background))
    return (lighter + 0.05) / (darker + 0.05)


def _fmt(value: float) -> str:
    return str(int(value)) if value == int(value) else str(value)


def _luminance(hex_color: str) -> float:
    digits = hex_color.lstrip("#")
    linear = []
    for index in (0, 2, 4):
        channel = int(digits[index : index + 2], 16) / 255
        if channel <= 0.03928:
            linear.append(channel / 12.92)
        else:
            linear.append(((channel + 0.055) / 1.055) ** 2.4)
    return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]
