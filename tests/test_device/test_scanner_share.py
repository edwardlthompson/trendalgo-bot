"""Scanner PNG export mirrors the dense table (sparks + heat) with filter caption."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
pytest.importorskip("PySide6")

from PySide6.QtWidgets import QApplication  # noqa: E402

from trendalgo.device.backtest_share import filter_summary  # noqa: E402
from trendalgo.device.scanner_share import (  # noqa: E402
    export_scanner_list_png,
    export_strategy_sheet_png,
    scanner_filter_summary,
)


@pytest.fixture(scope="module")
def qapp() -> QApplication:
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def test_scanner_filter_summary_lists_active_floors() -> None:
    assert "none" in scanner_filter_summary({}).lower()
    line = scanner_filter_summary(
        {
            "exchange": "Kraken",
            "min_volume_usd": 1_000_000,
            "min_gain_7d": 7,
            "min_gain_30d": 30,
            "heatmap_enabled": True,
        }
    )
    assert "min vol$=1,000,000" in line
    assert "min 7d%=7" in line
    assert "min 30d%=30" in line
    assert "color ranks=True" in line


def test_results_sheet_filter_summary_includes_column_floors() -> None:
    line = filter_summary({"min_net_pct": 30, "min_win_pct": 50, "max_tsl_hit_pct": 50})
    assert "min net%=30" in line
    assert "min win%=50" in line
    assert "max hit%=50" in line
    assert "none" not in line.lower()


def test_export_strategy_sheet_png_forwards_filters(
    qapp: QApplication, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    captured: dict[str, object] = {}

    def _fake(path: Path, **kwargs: object) -> Path:
        captured.update(kwargs)
        path.write_bytes(b"\x89PNG\r\n\x1a\n")
        return path

    monkeypatch.setattr(
        "trendalgo.device.backtest_share.export_backtest_table_png",
        _fake,
    )
    out = tmp_path / "ake.png"
    export_strategy_sheet_png(
        out,
        pair="AKE/USD",
        rows=[{"indicator": "RSI", "net_pct": 40.0}],
        heatmap=False,
        filters={"min_net_pct": 30, "min_win_pct": 50, "max_tsl_hit_pct": 50},
    )
    assert captured.get("filters") == {
        "min_net_pct": 30,
        "min_win_pct": 50,
        "max_tsl_hit_pct": 50,
    }


def test_export_scanner_list_png_writes_file(qapp: QApplication, tmp_path: Path) -> None:
    coins = [
        {
            "symbol": "BTC",
            "name": "Bitcoin",
            "pair": "BTC/USD",
            "gains": {"7d": 5.0, "30d": 12.0},
            "spark_closes_7d": [1.0, 1.1, 1.2, 1.15, 1.25],
            "spark_closes_30d": [1.0, 1.05, 1.1, 1.2, 1.3],
            "bot_best_net_pct": 40.0,
            "bot_vs_bh_pct": 8.0,
            "uniformity_score": 80.0,
            "health_score": 70.0,
            "hv_7d_pct": 40.0,
            "max_drawdown_pct": 12.0,
            "volume_acceleration_pct": 5.0,
            "listed_on": ["kraken"],
            "volume_24h": 2_000_000,
        }
    ]
    out = tmp_path / "scanner.png"
    path = export_scanner_list_png(
        out,
        coins=coins,
        title="Scanner · 1 pairs",
        filters={"min_gain_7d": 7, "min_volume_usd": 1_000_000},
        heatmap=True,
        sort_key="health",
        sort_dir=-1,
    )
    assert path == out
    assert out.is_file()
    assert out.stat().st_size > 500
