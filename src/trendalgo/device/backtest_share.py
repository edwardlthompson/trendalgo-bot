"""Export the filtered Backtest results table as a tight PNG (not a screen grab)."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from trendalgo.device.backtest_export_render import build_export_panel


def default_export_path(root: Path, *, pair: str) -> Path:
    day = datetime.now(tz=UTC).date().isoformat()
    safe = "".join(ch if ch.isalnum() or ch in "-_" else "-" for ch in pair.upper()) or "PAIR"
    return root / "exports" / f"backtest-{safe}-{day}.png"


def filter_summary(filters: dict[str, Any]) -> str:
    """Human-readable active filters for the export caption."""
    if not filters:
        return "Filters: (none)"
    labels = {
        "indicator_contains": "indicator",
        "timeframe": "tf",
        "params_contains": "params",
        "min_net_pct": "min net%",
        "max_fees": "max fees",
        "max_open": "max open",
        "min_wins": "min wins",
        "max_losses": "max losses",
        "min_win_pct": "min win%",
        "max_tsl_pct": "max tsl%",
        "max_tsl_hits": "max hits",
        "max_tsl_hit_pct": "max hit%",
        "min_strength": "min strength",
    }
    parts = [f"{labels[k]}={filters[k]}" for k in labels if k in filters]
    return "Filters: " + (", ".join(parts) if parts else "(none)")


def export_backtest_table_png(
    path: Path,
    *,
    pair: str,
    rows: list[dict[str, Any]],
    filters: dict[str, Any],
    heatmap: bool,
    sort_key: str,
    sort_dir: int,
) -> Path:
    """Render filtered rows + active filters into a content-sized PNG at *path*."""
    if not rows:
        raise ValueError("no rows to export")
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    panel = build_export_panel(
        pair=pair,
        rows=rows,
        filter_line=filter_summary(filters),
        heatmap=heatmap,
        sort_key=sort_key,
        sort_dir=sort_dir,
    )
    try:
        panel.adjustSize()
        pix = panel.grab()
        if pix.isNull() or not pix.save(str(path), "PNG"):
            raise OSError(f"failed to save backtest PNG to {path}")
    finally:
        panel.deleteLater()
    return path
