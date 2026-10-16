"""Shared results view prefs + Perfect Strategies + TSL display."""

from __future__ import annotations

from pathlib import Path

from trendalgo.device.backtest_results_ui import (
    filter_perfect_rows,
    format_export_params,
    is_perfect_strategy,
    tsl_display_pct,
)
from trendalgo.device.results_view_prefs import (
    ResultsViewPrefs,
    load_results_prefs,
    save_results_prefs,
)


def test_tsl_one_percent_not_hundred() -> None:
    assert tsl_display_pct(1.0) == 1
    assert tsl_display_pct(0.01) == 1
    assert tsl_display_pct(0.05) == 5
    assert tsl_display_pct(20) == 20
    text = format_export_params(
        {"params": {"timeperiod": 14}, "trailing_stop_pct": 1.0}, is_bh=False
    )
    assert "tsl=1%" in text
    assert "tsl=100%" not in text


def test_perfect_filter() -> None:
    rows = [
        {"indicator": "RSI", "win_pct": 100.0, "tsl_hits": 0, "net_pct": 5},
        {"indicator": "MACD", "win_pct": 100.0, "tsl_hits": 2, "net_pct": 8},
        {"indicator": "SMA", "win_pct": 80.0, "tsl_hits": 0, "net_pct": 3},
        {"indicator": "B&H", "win_pct": "-", "tsl_hits": 0, "net_pct": 1},
    ]
    assert is_perfect_strategy(rows[0])
    assert not is_perfect_strategy(rows[1])
    out = filter_perfect_rows(rows)
    assert [r["indicator"] for r in out] == ["RSI", "B&H"]


def test_prefs_roundtrip(tmp_path: Path) -> None:
    save_results_prefs(
        tmp_path,
        ResultsViewPrefs(
            heatmap_enabled=True,
            perfect_only=True,
            last_pair="ETH/USD",
            results_dialog_width=900,
            results_dialog_height=600,
            results_dialog_maximized=True,
        ),
    )
    loaded = load_results_prefs(tmp_path)
    assert loaded.heatmap_enabled is True
    assert loaded.perfect_only is True
    assert loaded.last_pair == "ETH/USD"
    assert loaded.results_dialog_width == 900
    assert loaded.results_dialog_height == 600
    assert loaded.results_dialog_maximized is True


def test_prefs_dialog_size_floors_to_minimum(tmp_path: Path) -> None:
    save_results_prefs(
        tmp_path,
        ResultsViewPrefs(results_dialog_width=100, results_dialog_height=50),
    )
    # Write tiny values directly so load clamps (dataclass allows constructing tiny ints).
    from trendalgo.device.profile import write_json
    from trendalgo.device.results_view_prefs import PREFS_FILE

    write_json(
        tmp_path / PREFS_FILE,
        {
            "heatmap_enabled": False,
            "perfect_only": False,
            "last_pair": "BTC/USD",
            "results_dialog_width": 100,
            "results_dialog_height": 50,
            "results_dialog_maximized": False,
        },
    )
    loaded = load_results_prefs(tmp_path)
    assert loaded.results_dialog_width == 520
    assert loaded.results_dialog_height == 360
