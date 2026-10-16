"""Share Portfolio tab as a PNG under exports/."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from PySide6.QtWidgets import QWidget


def share_widget_png(widget: QWidget, root: Path, *, tab: str) -> Path:
    """Grab *widget* and save ``exports/portfolio-{tab}-{date}.png``."""
    day = datetime.now(tz=UTC).date().isoformat()
    safe = "".join(ch if ch.isalnum() or ch in "-_" else "-" for ch in tab.lower()) or "tab"
    out = root / "exports" / f"portfolio-{safe}-{day}.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    pix = widget.grab()
    if not pix.save(str(out), "PNG"):
        raise OSError(f"failed to save share PNG to {out}")
    return out
