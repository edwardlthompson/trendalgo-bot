"""Results popup uses the same column filters as the Backtest tab."""

from __future__ import annotations

from pathlib import Path

from trendalgo.device.backtest_row_filter import filter_rows
from trendalgo.device.scanner_signal_sets import BT_SET_ALL_TA
from trendalgo.device.views.scanner_results import strategy_sheet_rows


def _coin() -> dict:
    return {
        "symbol": "BTC",
        "pair": "BTC/USD",
        "bt_signal_set": BT_SET_ALL_TA,
        "backtest_top_strategies": [
            {"indicator": "RSI", "timeframe": "1h", "net_pct": 12.0, "trades": 10},
            {"indicator": "MACD", "timeframe": "4h", "net_pct": 8.0, "trades": 6},
            {"indicator": "EMA Cross", "timeframe": "1h", "net_pct": 5.0, "trades": 4},
        ],
        "backtest_buy_hold": {"indicator": "B&H", "net_pct": 3.0},
    }


def test_results_column_filters_narrow_like_backtest() -> None:
    rows = strategy_sheet_rows(_coin(), perfect_only=False)
    names = {str(r.get("indicator")) for r in rows}
    assert "RSI" in names and "MACD" in names and "B&H" in names
    filtered = filter_rows(rows, {"timeframe": "1h", "indicator_contains": "rsi"})
    kept = [str(r.get("indicator")) for r in filtered]
    assert "RSI" in kept
    assert "MACD" not in kept
    assert "EMA Cross" not in kept
    # B&H always kept by filter_rows
    assert "B&H" in kept


def test_results_dialog_wires_column_filter_row() -> None:
    path = (
        Path(__file__).resolve().parents[2]
        / "src"
        / "trendalgo"
        / "device"
        / "views"
        / "scanner_results.py"
    )
    source = path.read_text(encoding="utf-8")
    assert "BacktestColumnFilterRow" in source
    assert "filter_rows" in source
    assert "_FILTER_DEBOUNCE_MS" in source
