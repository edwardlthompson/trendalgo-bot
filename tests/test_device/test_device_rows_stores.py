"""Display rows and read-only stores. Missing files give empty results and are never created."""

from __future__ import annotations

import math
from datetime import UTC, datetime
from pathlib import Path

import pytest

from trendalgo.bots.orchestrator import BotOrchestrator
from trendalgo.device import strings as S
from trendalgo.device.rows import (
    backtest_trade_rows,
    bot_rows,
    scan_caption,
    scan_rows,
    sparkline,
    trade_rows,
)
from trendalgo.device.stores import StoreReadError, read_bots, read_snapshot, read_trades
from trendalgo.scanner.snapshot import OpportunityRow, QualifiedSnapshot
from trendalgo.scanner.store import ScannerStore


def _snapshot(*, degraded: bool = False) -> QualifiedSnapshot:
    return QualifiedSnapshot(
        generated_at=datetime(2026, 10, 9, 12, 0, tzinfo=UTC),
        as_of=datetime(2026, 10, 9, 12, 0, tzinfo=UTC),
        scan_id=3,
        degraded=degraded,
        opportunities=[
            OpportunityRow(
                rank=1,
                pair="BTC/USD",
                uniformity=0.9,
                gain_pct=2.5,
                volume_score=10.0,
                entry_signal=True,
                sparkline=[0.0, 1.0],
            ),
        ],
    )


def test_sparkline_draws_a_trend_and_handles_empty_and_flat_input() -> None:
    assert sparkline([]) == "-"
    assert sparkline([math.nan]) == "-"
    assert sparkline([1.0, 1.0]) == "▁▁"
    assert sparkline([0.0, 1.0]) == "▁█"
    assert sparkline([0.0, math.nan, 1.0]) == "▁█"


def test_scan_rows_and_caption_describe_the_snapshot() -> None:
    rows = scan_rows(_snapshot())
    assert len(rows) == 1
    assert (rows[0].rank, rows[0].pair, rows[0].gain, rows[0].entry) == (
        "1",
        "BTC/USD",
        "+2.50%",
        "Yes",
    )
    assert rows[0].trend == "▁█"
    assert "Scan 3 as of 2026-10-09 12:00 UTC" in scan_caption(_snapshot(), use_utc=True)
    assert S.SCANNER_DEGRADED in scan_caption(_snapshot(degraded=True), use_utc=True)
    assert scan_rows(None) == []
    assert scan_caption(None) == ""


def test_bot_and_trade_rows_show_money_and_time_plainly() -> None:
    bots = bot_rows(
        [
            {"label": "Alpha", "pair": "BTC/USD", "enabled": True, "equity_usd": 1000.0},
            {"label": "Beta", "pair": "ETH/USD", "enabled": False, "equity_usd": None},
        ],
    )
    assert [(b.state, b.equity) for b in bots] == [("On", "$1,000.00"), ("Off", "-")]
    trades = trade_rows(
        [
            {
                "created_at": "2026-10-09T12:34:56+00:00",
                "pair": "BTC/USD",
                "side": "sell",
                "pnl_usd": -5.0,
                "signal_source": None,
            },
        ],
    )
    assert (trades[0].time, trades[0].pnl, trades[0].source) == (
        "2026-10-09 12:34",
        "-$5.00",
        "-",
    )


def test_backtest_trade_rows_format_prices_and_percent() -> None:
    rows = backtest_trade_rows(
        [
            {
                "entry_time": "2026-10-09T12:00:00+00:00",
                "exit_time": "2026-10-09T15:00:00+00:00",
                "entry_price": 100.0,
                "exit_price": 102.5,
                "pnl_pct": 2.5,
                "exit_reason": "take profit",
            },
        ],
        use_utc=True,
    )
    assert rows == [
        (
            "2026-10-09 12:00 UTC",
            "2026-10-09 15:00 UTC",
            "100.0000",
            "102.5000",
            "+2.50%",
            "take profit",
        ),
    ]


def test_missing_stores_read_as_empty_and_are_not_created(tmp_path: Path) -> None:
    scanner = tmp_path / "scanner.db"
    bots = tmp_path / "bots.db"
    journal = tmp_path / "journal.db"
    assert read_snapshot(scanner) is None
    assert read_bots(bots) == []
    assert read_trades(journal) == []
    assert not scanner.exists() and not bots.exists() and not journal.exists()


def test_a_real_store_reads_through_the_device_api(tmp_path: Path) -> None:
    ScannerStore(tmp_path / "scanner.db")
    assert read_snapshot(tmp_path / "scanner.db") is None
    BotOrchestrator(tmp_path / "bots.db").add_bot("Alpha", "lts", "BTC/USD")
    labels = [bot["label"] for bot in read_bots(tmp_path / "bots.db")]
    assert labels == ["Alpha"]


@pytest.mark.parametrize("name", ["scanner.db", "bots.db"])
def test_a_corrupt_store_is_reported_by_name_not_hidden(tmp_path: Path, name: str) -> None:
    (tmp_path / name).write_bytes(b"this is not a sqlite database" * 64)
    reader = read_snapshot if name == "scanner.db" else read_bots
    with pytest.raises(StoreReadError, match=f"{name} cannot be read"):
        reader(tmp_path / name)
