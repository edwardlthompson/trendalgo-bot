"""Backtest PNG export renders a tight table (not a viewport grab)."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
pytest.importorskip("PySide6")

from PySide6.QtWidgets import QApplication  # noqa: E402

from trendalgo.device.backtest_share import (  # noqa: E402
    default_export_path,
    export_backtest_table_png,
    filter_summary,
)


@pytest.fixture(scope="module")
def qapp() -> QApplication:
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def test_filter_summary_lists_active_filters() -> None:
    assert "none" in filter_summary({}).lower()
    assert "min wins=3" in filter_summary({"min_wins": 3})


def test_export_backtest_table_png_writes_file(qapp: QApplication, tmp_path: Path) -> None:
    rows = [
        {
            "indicator": "RSI",
            "timeframe": "1h",
            "params": {"timeperiod": 14},
            "net_pct": 12.5,
            "fees_paid": 1.2,
            "trades": 10,
            "wins": 7,
            "win_pct": 70.0,
            "trailing_stop_loss_pct": 0.05,
            "tsl_hits": 1,
        }
    ]
    out = tmp_path / "chart.png"
    path = export_backtest_table_png(
        out,
        pair="BTC/USD",
        rows=rows,
        filters={"min_wins": 3},
        heatmap=True,
        sort_key="net_pct",
        sort_dir=-1,
    )
    assert path == out
    assert out.is_file()
    assert out.stat().st_size > 500


def test_default_export_path_uses_pair(tmp_path: Path) -> None:
    path = default_export_path(tmp_path, pair="BTC/USD")
    assert path.parent == tmp_path / "exports"
    assert "BTC-USD" in path.name or "BTC" in path.name
