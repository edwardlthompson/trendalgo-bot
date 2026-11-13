"""Shared scan progress dialog helpers + pair glance."""

from __future__ import annotations

from trendalgo.device.views.scan_progress_dialog import (
    format_pair_label,
    format_pairs_remaining,
    glance_from_progress,
)
from trendalgo.scanner.progress import ScanProgress


def test_format_pair_label() -> None:
    assert format_pair_label("btc") == "BTC/USD"
    assert format_pair_label("eth/usd") == "ETH/USD"
    assert format_pair_label(None) == "—"


def test_format_pairs_remaining() -> None:
    assert "3 remaining" in format_pairs_remaining(done=12, total=15)
    assert "—" in format_pairs_remaining(done=0, total=None)


def test_glance_from_progress_reads_state_pair_fields() -> None:
    raw = {
        "message": "Backtesting…",
        "state": {
            "step_done": 40,
            "step_total": 100,
            "step_unit": "backtests",
            "current_pair": "SOL",
            "pairs_done": 2,
            "pairs_total": 10,
        },
    }
    glance = glance_from_progress(raw)
    assert glance["done"] == 40
    assert glance["total"] == 100
    assert glance["unit"] == "backtests"
    assert glance["current_pair"] == "SOL/USD"
    assert glance["pairs_done"] == 2
    assert glance["pairs_total"] == 10


def test_scan_progress_stamps_pair_fields_on_bt_events() -> None:
    prog = ScanProgress()
    prog.begin_job("Scan")
    prog.backtest_event(
        {
            "event": "bt_run_start",
            "total": 3,
            "indicators": 2,
            "timeframes": ["1h"],
        }
    )
    snap = prog.snapshot()
    assert snap["state"]["pairs_total"] == 3
    assert snap["state"]["pairs_done"] == 0
    prog.backtest_event({"event": "bt_heartbeat", "running": [("BTC", 1.0)], "pending_count": 2})
    assert snap_state_pair(prog) == "BTC/USD"
    prog.backtest_event(
        {
            "event": "bt_coin_done",
            "symbol": "ETH",
            "completed": 1,
            "total": 3,
            "rows": 5,
            "skipped": 0,
        }
    )
    state = prog.snapshot()["state"]
    assert state["current_pair"] == "ETH/USD"
    assert state["pairs_done"] == 1
    assert state["pairs_total"] == 3
    prog.end_job()


def snap_state_pair(prog: ScanProgress) -> str:
    return str(prog.snapshot()["state"]["current_pair"])
