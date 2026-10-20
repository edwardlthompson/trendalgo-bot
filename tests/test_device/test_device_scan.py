"""Device scan (D-02): the scan job, its progress file, and the pure helpers. Offline; no Qt and no Kraken."""

from __future__ import annotations

import hashlib
import sqlite3
from contextlib import closing
from datetime import UTC, datetime
from pathlib import Path

import pytest

from trendalgo.device.context import DeviceContext, open_context
from trendalgo.device.profile import DATA_ENV
from trendalgo.device.scan_job import scan_job
from trendalgo.device.scan_model import (
    ScanUnavailableError,
    device_scan_settings,
    progress_line,
    progress_pct,
    scan_store_path,
)
from trendalgo.device.scan_offline import OFFLINE_PAIRS, offline_listings, offline_market
from trendalgo.device.scan_progress import (
    ProgressReporter,
    clear_progress,
    consume_progress_events,
    read_progress,
)
from trendalgo.device.stores import read_snapshot
from trendalgo.scanner.config import default_scanner_settings
from trendalgo.scanner.listings import DEFAULT_KRAKEN_SPOT
from trendalgo.scanner.live_market import LiveMarketRow
from trendalgo.scanner.progress import get_scan_progress
from trendalgo.scanner.snapshot import OpportunityRow, QualifiedSnapshot
from trendalgo.scanner.store import ScannerStore


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _snapshot(generated: datetime) -> QualifiedSnapshot:
    return QualifiedSnapshot(
        generated_at=generated,
        as_of=generated,
        scan_id=1,
        degraded=False,
        opportunities=[
            OpportunityRow(
                rank=1,
                pair="BTC/USD",
                uniformity=0.9,
                gain_pct=2.5,
                volume_score=10.0,
                entry_signal=True,
                sparkline=[0.0, 1.0],
            )
        ],
    )


def test_a_scan_is_saved_on_this_pc_and_the_shared_file_is_not_changed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    shared = tmp_path / "data"
    ScannerStore(shared / "scanner.db").save_snapshot(_snapshot(datetime(2026, 10, 9, tzinfo=UTC)))
    before = _digest(shared / "scanner.db")
    monkeypatch.setenv(DATA_ENV, str(shared))
    ctx = open_context(tmp_path / "profile")
    with offline_listings():
        result = scan_job(ctx.root, fetcher=offline_market)
    assert int(result["scan_id"]) >= 1
    assert _digest(shared / "scanner.db") == before
    with closing(sqlite3.connect(scan_store_path(ctx.root))) as conn:
        assert conn.execute("PRAGMA journal_mode").fetchone()[0] == "wal"


def test_a_saved_scan_reads_back_as_this_pcs_latest(ctx: DeviceContext) -> None:
    with offline_listings():
        scan_job(ctx.root, fetcher=offline_market)
    snapshot = read_snapshot(scan_store_path(ctx.root))
    assert snapshot is not None
    assert snapshot.degraded is False


def test_a_failed_live_fetch_is_an_error_and_saves_nothing(tmp_path: Path) -> None:
    def broken(_pairs: list[str]) -> list[LiveMarketRow]:
        raise ConnectionError("kraken unreachable")

    ctx = open_context(tmp_path / "profile")
    with offline_listings(), pytest.raises(ScanUnavailableError):
        scan_job(ctx.root, fetcher=broken)
    assert not scan_store_path(ctx.root).exists()


def test_the_fallback_pair_list_is_an_error_and_saves_nothing(tmp_path: Path) -> None:
    ctx = open_context(tmp_path / "profile")
    with offline_listings(pairs=DEFAULT_KRAKEN_SPOT), pytest.raises(ScanUnavailableError):
        scan_job(ctx.root, fetcher=offline_market)
    assert not scan_store_path(ctx.root).exists()


def test_the_progress_file_carries_the_latest_message_and_state(ctx: DeviceContext) -> None:
    get_scan_progress().log("unit test marker")
    reporter = ProgressReporter(ctx.root, interval_s=0.05)
    reporter.start()
    reporter.stop()
    progress = read_progress(ctx.root)
    assert progress is not None
    assert progress["message"] == "unit test marker"
    assert "status" in progress["state"]
    clear_progress(ctx.root)
    assert read_progress(ctx.root) is None


def test_progress_file_keeps_event_ring_for_log_append(ctx: DeviceContext) -> None:
    progress = get_scan_progress()
    progress.log("alpha event")
    progress.log("beta event")
    reporter = ProgressReporter(ctx.root, interval_s=0.05)
    reporter.start()
    reporter.stop()
    raw = read_progress(ctx.root)
    assert raw is not None
    assert int(raw.get("last_seq") or 0) >= 2
    lines, cursor = consume_progress_events(raw, 0)
    assert "alpha event" in lines
    assert "beta event" in lines
    again, cursor2 = consume_progress_events(raw, cursor)
    assert again == []
    assert cursor2 == cursor
    clear_progress(ctx.root)


def test_consume_progress_events_skips_seen_seq() -> None:
    raw = {
        "events": [
            {"seq": 1, "message": "one"},
            {"seq": 2, "message": "two"},
            {"seq": 3, "message": "three"},
        ],
        "last_seq": 3,
    }
    first, mid = consume_progress_events(raw, 1)
    assert first == ["two", "three"]
    assert mid == 3


def test_the_progress_line_names_the_phase_the_count_and_the_message() -> None:
    progress = {
        "state": {
            "phase": "Scan 3/3 · uniformity gate + rank",
            "step_done": 40,
            "step_total": 200,
            "step_unit": "pairs",
        },
        "message": "Qualified 2 of 200 pairs",
    }
    assert progress_line(progress) == (
        "Scan 3/3 · uniformity gate + rank · 40 of 200 pairs · Qualified 2 of 200 pairs"
    )
    assert progress_pct(progress) == 20
    assert progress_pct(None) is None
    assert progress_line(None) == ""
    assert progress_line({"state": {}, "message": ""}) == ""


def test_a_device_scan_uses_the_scanner_defaults_and_the_profile_folder(ctx: DeviceContext) -> None:
    assert device_scan_settings() == default_scanner_settings()
    assert scan_store_path(ctx.root) == ctx.root / "scanner.db"
    rows = offline_market(list(OFFLINE_PAIRS))
    assert [row.pair for row in rows] == list(OFFLINE_PAIRS)
