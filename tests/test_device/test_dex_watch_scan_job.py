"""DEX-P2a device job for thin pool watch."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from trendalgo.device.dex_watch_model import load_dex_watch_rows
from trendalgo.device.dex_watch_scan_job import dex_watch_scan_job
from trendalgo.device.support_matrix import clear_support_matrix_cache, venue_by_id
from trendalgo.venues.dex_watch_types import PoolWatchRow, PoolWatchSnapshot


def test_dex_watch_scan_job_persists(tmp_path: Path) -> None:
    result = dex_watch_scan_job(tmp_path)
    assert result["scan_mode"] == "dex_watch"
    assert result["rows"] >= 2
    assert set(result["venues"]) == {"ethereum", "base"}
    rows = load_dex_watch_rows(tmp_path)
    assert len(rows) == result["rows"]
    assert rows[0]["chart_closes"] == []


def test_dex_watch_scan_job_injectable_scanner(tmp_path: Path) -> None:
    snap = PoolWatchSnapshot(
        generated_at=datetime.now(UTC),
        rows=(
            PoolWatchRow(
                venue_id="base",
                pool_address="0xabc",
                pair="ETH/USDC",
                liquidity_usd=1.0,
                price_change_24h_pct=0.0,
                volume_proxy_usd=2.0,
                degraded=True,
                source="base_dry_run",
            ),
        ),
        degraded=True,
    )
    result = dex_watch_scan_job(tmp_path, scanner=lambda: snap)
    assert result["rows"] == 1
    assert result["venues"] == ["base"]


def test_matrix_ethereum_base_public_scan_thin() -> None:
    clear_support_matrix_cache()
    eth = venue_by_id("ethereum")
    base = venue_by_id("base")
    assert eth is not None and base is not None
    assert eth.public_scan == "thin"
    assert base.public_scan == "thin"
    assert not eth.public_scan_ready
