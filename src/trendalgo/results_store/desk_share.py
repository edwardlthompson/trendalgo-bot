"""Headless PNG exports for Avalonia share (board + strategy) — real Qt render, not a stub."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from trendalgo.device.export_prefs import remember_export_dir, suggested_png_path
from trendalgo.device.export_qt import ensure_export_qapp
from trendalgo.device.lts_scan_model import load_lts_rows


def _day() -> str:
    return datetime.now(tz=UTC).date().isoformat()


def _resolve_dest(root: Path, dest: Path | str | None, fallback_name: str) -> Path:
    if dest is not None and str(dest).strip():
        path = Path(dest)
        if path.suffix.lower() != ".png":
            path = Path(f"{path}.png")
        path.parent.mkdir(parents=True, exist_ok=True)
        return path
    return suggested_png_path(root, fallback_name)


def share_board_png(
    root: Path,
    *,
    lane: str = "crypto",
    limit: int = 200,
    dest: Path | str | None = None,
    pairs: list[str] | None = None,
    title: str | None = None,
    filter_line: str | None = None,
    filters: dict[str, Any] | None = None,
    include_market_context: bool = True,
) -> dict[str, Any]:
    from trendalgo.device.results_view_prefs import load_results_prefs
    from trendalgo.device.scanner_share import export_scanner_list_png

    rows = [r for r in load_lts_rows(root, lane=lane) if isinstance(r, dict)]
    if pairs:
        rows = _order_rows_by_pairs(rows, pairs)
    path = _resolve_dest(root, dest, f"board-{lane}-{_day()}.png")
    coins = rows[: max(1, limit)] if rows else []
    ensure_export_qapp(root, force_dark=True)
    prefs = load_results_prefs(root)
    active = dict(filters or {})
    if "heatmap_enabled" not in active:
        active["heatmap_enabled"] = bool(prefs.heatmap_enabled)
    # Collapsed MC on the desk → omit the band; when included, export every filtered coin.
    include_mc = bool(include_market_context) and not bool(active.pop("buy_picks_collapsed", False))
    label = (title or "").strip() or f"Scanner · {len(coins)} pairs"
    if not coins:
        _write_message_png(path, [label, "(no qualified rows)"])
    else:
        export_scanner_list_png(
            path,
            coins=coins,
            title=label,
            filters=active,
            filter_line=filter_line,
            heatmap=bool(active.get("heatmap_enabled")),
            include_market_context=include_mc,
            market_context_limit=None,
            icon_root=root,
            lane=lane,
        )
    remember_export_dir(root, path)
    return {
        "kind": "board",
        "lane": lane,
        "path": str(path),
        "rows": len(coins),
        "include_market_context": include_mc,
    }


def _order_rows_by_pairs(rows: list[dict[str, Any]], pairs: list[str]) -> list[dict[str, Any]]:
    """Keep only *pairs* (case-insensitive), in the caller’s visible order."""
    by: dict[str, dict[str, Any]] = {}
    for row in rows:
        key = str(row.get("pair") or "").strip().upper()
        if key:
            by[key] = row
    ordered: list[dict[str, Any]] = []
    for raw in pairs:
        key = str(raw or "").strip().upper()
        if key and key in by:
            ordered.append(by[key])
    return ordered


def share_dashboard_png(
    root: Path, *, limit: int = 40, dest: Path | str | None = None
) -> dict[str, Any]:
    """Export 2x high-DPI Executive Dashboard Share Card PNG via Qt."""
    del limit
    from trendalgo.device.portfolio_report_png import render_dashboard_report_png
    from trendalgo.results_store.desk_dashboard import load_dashboard_surface

    data = load_dashboard_surface(root)
    tiles_raw = data.get("tiles")
    tiles: list[Any] = tiles_raw if isinstance(tiles_raw, list) else []
    page = str(data.get("active_page_id") or "overview")
    path = _resolve_dest(root, dest, f"dashboard-{page}-{_day()}.png")
    render_dashboard_report_png(root, path)
    remember_export_dir(root, path)
    return {
        "kind": "dashboard",
        "page": page,
        "path": str(path),
        "rows": max(1, len(tiles)),
    }


def share_strategy_png(
    root: Path,
    *,
    pair: str,
    lane: str = "crypto",
    limit: int = 40,
    dest: Path | str | None = None,
) -> dict[str, Any]:
    from trendalgo.device.backtest_results_ui import rows_for_strategy_export
    from trendalgo.device.results_view_prefs import load_results_prefs
    from trendalgo.device.scanner_share import export_strategy_sheet_png
    from trendalgo.results_store.desk_surfaces import find_coin, strategy_sheet_from_coin

    pair_u = str(pair or "").strip().upper() or "BTC/USD"
    coin = find_coin(root, pair_u, lane=lane) or {"pair": pair_u}
    sheet = strategy_sheet_from_coin(coin)
    export_rows = rows_for_strategy_export(sheet)[: max(1, limit)]
    safe = pair_u.replace("/", "-")
    path = _resolve_dest(root, dest, f"strategy-{safe}-{_day()}.png")
    ensure_export_qapp(root, force_dark=True)
    prefs = load_results_prefs(root)
    raw_mc = coin.get("market_context")
    market_context = raw_mc if isinstance(raw_mc, dict) else None
    if not export_rows:
        _write_message_png(
            path,
            [f"{pair_u} · strategy sheet", "(no backtest rows yet — run a scan)"],
        )
    else:
        export_strategy_sheet_png(
            path,
            pair=pair_u,
            rows=export_rows,
            heatmap=bool(prefs.heatmap_enabled),
            filters={},
            market_context=market_context,
        )
    remember_export_dir(root, path)
    return {"kind": "strategy", "pair": pair_u, "path": str(path), "rows": len(sheet)}


def _write_message_png(path: Path, lines: list[str]) -> Path:
    """Small readable Qt panel when there is nothing to export."""
    from PySide6.QtGui import QFont
    from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget

    from trendalgo.device.theme import active_mode
    from trendalgo.device.theme_css import colors_for

    ensure_export_qapp(force_dark=True)
    theme = colors_for(active_mode())
    panel = QWidget()
    panel.setObjectName("panel")
    panel.setStyleSheet(
        f"QWidget#panel {{ background: {theme['surface']}; color: {theme['onSurface']}; }}"
    )
    layout = QVBoxLayout(panel)
    layout.setContentsMargins(16, 16, 16, 16)
    for i, line in enumerate(lines):
        lab = QLabel(line)
        if i == 0:
            font = QFont(lab.font())
            font.setBold(True)
            font.setPointSize(max(11, font.pointSize() + 1))
            lab.setFont(font)
        layout.addWidget(lab)
    panel.adjustSize()
    panel.setFixedWidth(max(420, panel.sizeHint().width()))
    panel.adjustSize()
    pix = panel.grab()
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if pix.isNull() or not pix.save(str(path), "PNG"):
        raise OSError(f"failed to save PNG to {path}")
    panel.deleteLater()
    return path
