"""Desk worker — process enqueue → progressive results.db (AV-G3)."""

from __future__ import annotations

import json
from pathlib import Path

from trendalgo.results_store.desk_commands import enqueue_command, peek_pending
from trendalgo.results_store.desk_worker import process_pending
from trendalgo.results_store.store import ResultsStore


def _seed_lts(root: Path, n: int = 5) -> None:
    rows = [
        {
            "pair": f"COIN{i}/USD",
            "symbol": f"COIN{i}",
            "exchange": "kraken",
            "gain": float(i),
            "volume_score": 1.0,
        }
        for i in range(n)
    ]
    (root / "lts_scan_rows.json").write_text(json.dumps({"rows": rows}), encoding="utf-8")


def test_process_run_scan_dry_publishes_opportunity_rows(tmp_path: Path) -> None:
    _seed_lts(tmp_path, 5)
    cid = enqueue_command(tmp_path, "run_scan", lane="crypto")
    result = process_pending(tmp_path, dry_run=True, batch_size=2)
    assert result is not None
    assert result["id"] == cid
    assert result["status"] == "done"
    assert result["rows"] == 5
    store = ResultsStore(tmp_path)
    try:
        assert store.job_state("scan:crypto") == "done"
        run_id = result["run_id"]
        assert store.count_opportunity_rows(run_id) == 5
    finally:
        store.close()
    assert peek_pending(tmp_path) is None


def test_cancel_scan_signals_and_acks(tmp_path: Path) -> None:
    enqueue_command(tmp_path, "run_scan", lane="crypto")
    cancel_id = enqueue_command(tmp_path, "cancel_scan", lane="crypto")
    result = process_pending(tmp_path, dry_run=True)
    assert result is not None
    assert result["id"] == cancel_id
    assert result["status"] == "done"
    assert result["action"] == "cancel_scan"
    store = ResultsStore(tmp_path)
    try:
        assert store.job_state("scan:crypto") == "cancelled"
    finally:
        store.close()


def test_process_run_scan_respects_cancel_mid_batch(tmp_path: Path) -> None:
    _seed_lts(tmp_path, 10)
    enqueue_command(tmp_path, "run_scan", lane="crypto")
    from trendalgo.results_store.desk_worker import request_cancel

    def on_batch(written: int) -> None:
        if written >= 3:
            request_cancel(tmp_path, "crypto")

    result = process_pending(tmp_path, dry_run=True, batch_size=3, on_batch=on_batch)
    assert result is not None
    assert result["status"] == "cancelled"
    assert 3 <= result["rows"] < 10


def test_run_sauce_dry_acks(tmp_path: Path) -> None:
    cid = enqueue_command(tmp_path, "run_sauce", lane="crypto")
    result = process_pending(tmp_path, dry_run=True)
    assert result is not None
    assert result["id"] == cid
    assert result["action"] == "run_sauce"
    assert result["status"] == "done"


def test_refresh_prices_dry_publishes(tmp_path: Path) -> None:
    _seed_lts(tmp_path, 3)
    cid = enqueue_command(tmp_path, "refresh_prices", lane="crypto")
    result = process_pending(tmp_path, dry_run=True, batch_size=10)
    assert result is not None
    assert result["id"] == cid
    assert result["action"] == "refresh_prices"
    assert result["status"] == "done"
    assert result["rows"] == 3


def test_pool_watch_dry_acks(tmp_path: Path) -> None:
    cid = enqueue_command(tmp_path, "pool_watch", lane="crypto")
    result = process_pending(tmp_path, dry_run=True)
    assert result is not None
    assert result["id"] == cid
    assert result["action"] == "pool_watch"
    assert result["status"] == "done"
