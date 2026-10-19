"""Backtest results polish: columns, asterisks, heat keys."""

from __future__ import annotations

from trendalgo.device import strings as S
from trendalgo.device.backtest_results_ui import HEAT_COLS, NET_COL, indicator_label, row_cells


def test_backtest_headers_order() -> None:
    assert S.BACKTEST_RESULT_HEADERS == (
        "Indicator",
        "Timeframe",
        "Params",
        "Net %",
        "Fees $",
        "Open",
        "Wins",
        "Losses",
        "Win %",
        "TSL",
        "TSL Hits",
        "TSL Hit %",
        "Strength",
        "Show Chart",
        "Create Bot",
    )
    assert NET_COL == 3


def test_three_commas_asterisk() -> None:
    assert indicator_label("RSI", is_bh=False).endswith(" *")
    assert "buy & hold" in indicator_label("B&H", is_bh=True)


def test_row_cells_params_and_order() -> None:
    cells = row_cells(
        {
            "indicator": "RSI",
            "timeframe": "1h",
            "params": {"timeperiod": 18, "entry_level": 25, "exit_level": 72},
            "net_pct": 12.5,
            "fees_paid": 10.4,
            "trades": 4,
            "open_trades": 1,
            "wins": 1,
            "win_pct": 50.0,
            "trailing_stop_pct": 2.0,
            "tsl_hits": 1,
        },
        is_bh=False,
    )
    assert cells[0] == "RSI *"
    assert "timeperiod=18" in cells[2]
    assert "entry_level=25" in cells[2]
    assert "tsl=2%" in cells[2]
    assert "12.5" in cells[3] or cells[3].endswith("%")
    assert cells[4] == "10.40"
    assert cells[5] == "1"  # open
    assert cells[6] == "1"  # wins among closed
    assert cells[7] == "2"  # losses among closed (3 closed - 1 win)
    assert NET_COL in HEAT_COLS
    assert HEAT_COLS[4] == ("fees_paid", True)
    assert HEAT_COLS[5] == ("open_trades", True)
    assert HEAT_COLS[6] == ("wins", False)
    assert HEAT_COLS[7] == ("losses", True)
    assert HEAT_COLS[10] == ("tsl_hits", True)
    assert HEAT_COLS[11] == ("tsl_hit_pct", True)
    assert HEAT_COLS[12] == ("strength", False)
