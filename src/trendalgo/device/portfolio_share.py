"""Share Dashboard page or module as a PNG under exports/."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from PySide6.QtGui import QPainter, QPixmap
from PySide6.QtWidgets import QWidget


def default_portfolio_export_path(root: Path, *, label: str) -> Path:
    day = datetime.now(tz=UTC).date().isoformat()
    safe = "".join(ch if ch.isalnum() or ch in "-_" else "-" for ch in label.lower()) or "page"
    return root / "exports" / f"portfolio-{safe}-{day}.png"


def share_widget_png(
    widget: QWidget,
    root: Path,
    *,
    tab: str,
    dest: Path | None = None,
) -> Path:
    """Grab *widget* and save a PNG (default under ``exports/``)."""
    out = dest if dest is not None else default_portfolio_export_path(root, label=tab)
    if not str(out).lower().endswith(".png"):
        out = Path(f"{out}.png")
    out.parent.mkdir(parents=True, exist_ok=True)
    pix = widget.grab()
    if pix.isNull() or pix.width() < 1 or pix.height() < 1:
        raise OSError("nothing to capture — wait for the Dashboard to finish loading")
    if not pix.save(str(out), "PNG"):
        raise OSError(f"failed to save share PNG to {out}")
    return out


def share_module_png(
    widget: QWidget,
    root: Path,
    *,
    module_id: str,
    dest: Path | None = None,
) -> Path:
    return share_widget_png(widget, root, tab=f"mod-{module_id}", dest=dest)


def share_page_png(
    widgets: list[QWidget],
    root: Path,
    *,
    page_id: str,
    dest: Path | None = None,
) -> Path:
    """Composite module grabs top-to-bottom into one page PNG."""
    out = dest if dest is not None else default_portfolio_export_path(root, label=f"page-{page_id}")
    if not str(out).lower().endswith(".png"):
        out = Path(f"{out}.png")
    out.parent.mkdir(parents=True, exist_ok=True)
    grabs: list[QPixmap] = []
    for w in widgets:
        if w is None:
            continue
        g = w.grab()
        if not g.isNull() and g.width() > 0 and g.height() > 0:
            grabs.append(g)
    if not grabs:
        raise OSError("no modules to export")
    width = max(g.width() for g in grabs)
    height = sum(g.height() for g in grabs)
    canvas = QPixmap(width, height)
    canvas.fill()
    painter = QPainter(canvas)
    y = 0
    for grab in grabs:
        painter.drawPixmap(0, y, grab)
        y += grab.height()
    painter.end()
    if not canvas.save(str(out), "PNG"):
        raise OSError(f"failed to save page PNG to {out}")
    return out
