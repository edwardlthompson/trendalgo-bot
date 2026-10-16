"""Export the filtered scanner list / results sheet as a PNG."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from trendalgo.device.scanner_export_render import build_scanner_export_panel


def default_scanner_export_path(root: Path, *, label: str) -> Path:
    day = datetime.now(tz=UTC).date().isoformat()
    safe = "".join(ch if ch.isalnum() or ch in "-_" else "-" for ch in label) or "scan"
    return root / "exports" / f"scanner-{safe}-{day}.png"


def scanner_filter_summary(filters: dict[str, Any]) -> str:
    """Human-readable active scanner filters for the export caption."""
    if not filters:
        return "Filters: (none)"
    labels = {
        "exchange": "exchange",
        "min_volume_usd": "min vol$",
        "min_gain_7d": "min 7d%",
        "min_gain_30d": "min 30d%",
        "min_gain_pct": "min 30d%",
        "min_best_bt": "min best bt%",
        "bot_vs_bh_filter": "bot vs b&h",
        "chart_dist_max_7d": "max dist 7d%",
        "chart_dist_max_30d": "max dist 30d%",
        "health_min": "min health",
        "uniformity_min": "min uniformity",
        "vol_accel_filter": "vol Δ",
        "vol24_min": "min 24h vol$",
        "bt_signal_set": "signals",
        "heatmap_enabled": "color ranks",
        "perfect_only": "perfect only",
    }
    parts: list[str] = []
    seen: set[str] = set()
    for key, label in labels.items():
        if key not in filters or label in seen:
            continue
        raw = filters[key]
        if raw in (None, "", 0, 0.0, False, "All", "all"):
            continue
        if key == "heatmap_enabled" and not raw:
            continue
        if key == "perfect_only" and not raw:
            continue
        if key == "min_volume_usd" or key == "vol24_min":
            try:
                parts.append(f"{label}={float(raw):,.0f}")
            except (TypeError, ValueError):
                parts.append(f"{label}={raw}")
        else:
            parts.append(f"{label}={raw}")
        seen.add(label)
    return "Filters: " + (", ".join(parts) if parts else "(none)")


def export_scanner_list_png(
    path: Path,
    *,
    coins: list[dict[str, Any]],
    title: str,
    filters: dict[str, Any] | None = None,
    heatmap: bool = False,
    sort_key: str = "health",
    sort_dir: int = -1,
) -> Path:
    if not coins:
        raise ValueError("no rows to export")
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    panel = build_scanner_export_panel(
        coins=coins,
        title=title,
        filter_line=scanner_filter_summary(filters or {}),
        heatmap=heatmap,
        sort_key=sort_key,
        sort_dir=sort_dir,
    )
    try:
        panel.adjustSize()
        pix = panel.grab()
        if pix.isNull() or not pix.save(str(path), "PNG"):
            raise OSError(f"failed to save scanner PNG to {path}")
    finally:
        panel.deleteLater()
    return path


def export_strategy_sheet_png(
    path: Path,
    *,
    pair: str,
    rows: list[dict[str, Any]],
    heatmap: bool,
    sort_key: str = "net_pct",
    sort_dir: int = -1,
) -> Path:
    from trendalgo.device.backtest_share import export_backtest_table_png

    return export_backtest_table_png(
        path,
        pair=pair,
        rows=rows,
        filters={},
        heatmap=heatmap,
        sort_key=sort_key,
        sort_dir=sort_dir,
    )
