"""Save-dialog + confirmation for Backtest PNG export."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from PySide6.QtWidgets import QFileDialog, QMessageBox, QWidget

from trendalgo.device import strings as S
from trendalgo.device.backtest_share import default_export_path, export_backtest_table_png


def run_backtest_share_dialog(
    parent: QWidget,
    *,
    root: Path,
    pair: str,
    rows: list[dict[str, Any]],
    filters: dict[str, Any],
    heatmap: bool,
    sort_key: str,
    sort_dir: int,
) -> str | None:
    """Show save dialog, export, confirm. Returns status note or None when cancelled."""
    if not rows:
        QMessageBox.information(parent, S.BACKTEST_SHARE, S.BACKTEST_SHARE_NEED_ROWS)
        return None
    suggested = str(default_export_path(root, pair=pair))
    chosen, _flt = QFileDialog.getSaveFileName(
        parent,
        S.BACKTEST_SHARE_DIALOG,
        suggested,
        S.BACKTEST_SHARE_FILTER,
    )
    if not chosen:
        return None
    out = Path(chosen) if chosen.lower().endswith(".png") else Path(f"{chosen}.png")
    try:
        export_backtest_table_png(
            out,
            pair=pair,
            rows=rows,
            filters=filters,
            heatmap=heatmap,
            sort_key=sort_key,
            sort_dir=sort_dir,
        )
    except (OSError, ValueError) as exc:
        QMessageBox.warning(parent, S.BACKTEST_SHARE, str(exc))
        return str(exc)
    note = S.BACKTEST_SHARE_DONE.format(name=out.name, path=str(out.parent))
    QMessageBox.information(parent, S.BACKTEST_SHARE, note)
    return note
