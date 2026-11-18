"""Fiat currency icon pool for the Forex desk (ISO code → glyph mark PNG)."""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

_MODULE_REPO = Path(__file__).resolve().parents[3]
_SUFFIXES = (".png", ".PNG")

# Glyph + mid-luminance RGB for each ISO code used by forex_universe (+ common extras).
CURRENCY_MARKS: dict[str, tuple[str, tuple[int, int, int]]] = {
    "USD": ("$", (37, 99, 235)),
    "EUR": ("€", (37, 99, 180)),
    "GBP": ("£", (99, 102, 241)),
    "JPY": ("¥", (220, 38, 38)),
    "CHF": ("Fr", (220, 38, 38)),
    "AUD": ("A$", (16, 185, 129)),
    "CAD": ("C$", (220, 38, 38)),
    "NZD": ("NZ$", (15, 118, 110)),
    "SEK": ("kr", (14, 165, 233)),
    "NOK": ("kr", (59, 130, 246)),
    "DKK": ("kr", (220, 38, 38)),
    "SGD": ("S$", (244, 63, 94)),
    "HKD": ("HK$", (220, 38, 38)),
    "MXN": ("$", (22, 163, 74)),
    "ZAR": ("R", (34, 197, 94)),
    "TRY": ("₺", (239, 68, 68)),
    "PLN": ("zł", (220, 38, 38)),
    "CNH": ("¥", (220, 38, 38)),
    "INR": ("₹", (249, 115, 22)),
    "THB": ("฿", (168, 85, 247)),
    "KRW": ("₩", (59, 130, 246)),
    "TWD": ("NT$", (14, 165, 233)),
    "BRL": ("R$", (34, 197, 94)),
    "CLP": ("$", (14, 165, 233)),
    "COP": ("$", (249, 115, 22)),
    "ARS": ("$", (59, 130, 246)),
    "HUF": ("Ft", (99, 102, 241)),
    "CZK": ("Kč", (14, 165, 233)),
}


def currency_codes_for_universe() -> tuple[str, ...]:
    from trendalgo.brokers.forex_universe import load_forex_universe

    codes: set[str] = set()
    for pair in load_forex_universe():
        base, _, quote = pair.partition("/")
        if base:
            codes.add(base.upper())
        if quote:
            codes.add(quote.upper())
    # Always keep the curated mark table available even if universe shrinks.
    codes.update(CURRENCY_MARKS)
    return tuple(sorted(codes))


def currency_icon_dirs() -> tuple[Path, ...]:
    folders: list[Path] = []
    env = os.environ.get("TRENDALGO_CURRENCY_ICONS", "").strip()
    if env:
        folders.append(Path(env))
    folders.append(_MODULE_REPO / "branding" / "assets" / "currencies")
    return tuple(folder for folder in folders if folder.is_dir() or folder == folders[-1])


def currency_pool_dir() -> Path:
    """Canonical on-disk pool (created when we generate marks)."""
    path = _MODULE_REPO / "branding" / "assets" / "currencies"
    path.mkdir(parents=True, exist_ok=True)
    return path


@lru_cache(maxsize=64)
def currency_icon_path(code: str) -> Path | None:
    ccy = (code or "").strip().upper()
    if not ccy:
        return None
    for folder in currency_icon_dirs():
        if not folder.is_dir():
            continue
        for suffix in _SUFFIXES:
            candidate = folder / f"{ccy}{suffix}"
            if candidate.is_file() and candidate.stat().st_size > 32:
                return candidate
    return None


def clear_currency_icon_cache() -> None:
    currency_icon_path.cache_clear()


def ensure_currency_icon(code: str, *, size: int = 64) -> Path | None:
    """Return pool PNG for ``code``, generating a glyph mark when missing."""
    ccy = (code or "").strip().upper()
    if not ccy:
        return None
    existing = currency_icon_path(ccy)
    if existing is not None:
        return existing
    glyph, rgb = CURRENCY_MARKS.get(ccy, (ccy[:2], _fallback_rgb(ccy)))
    dest = currency_pool_dir() / f"{ccy}.png"
    if _paint_currency_png(dest, glyph=glyph, label=ccy, rgb=rgb, size=size):
        clear_currency_icon_cache()
        return dest if dest.is_file() else None
    return None


def ensure_universe_currency_icons(*, size: int = 64) -> list[Path]:
    """Materialize every ISO code used by the Forex universe into the icon pool."""
    out: list[Path] = []
    for code in currency_codes_for_universe():
        path = ensure_currency_icon(code, size=size)
        if path is not None:
            out.append(path)
    return out


def _fallback_rgb(code: str) -> tuple[int, int, int]:
    seed = sum(ord(c) for c in code) * 17
    return (80 + (seed % 127), 80 + ((seed // 3) % 127), 80 + ((seed // 7) % 127))


def _paint_currency_png(
    dest: Path,
    *,
    glyph: str,
    label: str,
    rgb: tuple[int, int, int],
    size: int,
) -> bool:
    try:
        from PySide6.QtCore import Qt
        from PySide6.QtGui import QColor, QFont, QPainter, QPixmap
    except ImportError:
        return False
    pix = QPixmap(size, size)
    pix.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pix)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setBrush(QColor(*rgb))
    painter.setPen(QColor(255, 255, 255, 40))
    painter.drawRoundedRect(1, 1, size - 2, size - 2, max(6, size // 8), max(6, size // 8))
    painter.setPen(QColor(255, 255, 255))
    gfont = QFont()
    gfont.setBold(True)
    gfont.setPixelSize(max(14, size // 2 - (2 if len(glyph) > 1 else 0)))
    painter.setFont(gfont)
    glyph_rect = pix.rect().adjusted(2, 2, -2, -size // 3)
    painter.drawText(glyph_rect, int(Qt.AlignmentFlag.AlignCenter), glyph[:3])
    lfont = QFont()
    lfont.setBold(True)
    lfont.setPixelSize(max(8, size // 5))
    painter.setFont(lfont)
    painter.setPen(QColor(255, 255, 255, 220))
    label_rect = pix.rect().adjusted(2, size // 2 + size // 10, -2, -2)
    painter.drawText(label_rect, int(Qt.AlignmentFlag.AlignCenter), label[:3])
    painter.end()
    dest.parent.mkdir(parents=True, exist_ok=True)
    return bool(pix.save(str(dest), "PNG"))
