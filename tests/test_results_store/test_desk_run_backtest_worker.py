"""AV-G-OTH5 — run_backtest executes All-TA worker (not JSON republish)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from trendalgo.device.last_pair_backtest import load_last_pair_backtest
from trendalgo.results_store.desk_commands import enqueue_command, peek_pending
from trendalgo.results_store.desk_jobs import handle_run_backtest
from trendalgo.results_store.desk_worker import process_pending


def _fake_scan(root: Path, pair: str) -> dict[str, Any]:
    return {
        "rows": [
            {"indicator": "RSI", "net_pct": 11.0, "timeframe": "1h", "trades": 4},
            {"indicator": "B&H", "net_pct": 2.0, "timeframe": "1h", "trades": 1},
        ],
        "market_context": {"regime": "test"},
        "elapsed_s": 0.01,
        "data_source": "synthetic",
    }


def test_handle_run_backtest_runs_job_and_persists(tmp_path: Path) -> None:
    cid = enqueue_command(tmp_path, "run_backtest", lane="crypto", params={"pair": "BTC/USD"})
    result = handle_run_backtest(
        tmp_path,
        cid,
        "run_backtest",
        "crypto",
        params={"pair": "BTC/USD"},
        scan_job=_fake_scan,
    )
    assert result["status"] == "done"
    assert result["rows"] == 2
    saved = load_last_pair_backtest(tmp_path)
    assert saved is not None
    pair, rows, ctx = saved
    assert pair == "BTC/USD"
    assert len(rows) == 2
    assert ctx == {"regime": "test"}


def test_process_pending_run_backtest_dry_acks(tmp_path: Path) -> None:
    enqueue_command(tmp_path, "run_backtest", lane="crypto", params={"pair": "ETH/USD"})
    out = process_pending(tmp_path, dry_run=True)
    assert out is not None
    assert out["action"] == "run_backtest"
    assert out["status"] == "done"
    assert peek_pending(tmp_path) is None
