"""Pure tests for device AI curated library and recommendations."""

from __future__ import annotations

from datetime import UTC, datetime

from trendalgo.device.ai_model import curated_library, device_recommendations
from trendalgo.scanner.snapshot import OpportunityRow, QualifiedSnapshot
from trendalgo.scanner.store import ScannerStore


def test_curated_library_has_presets() -> None:
    data = curated_library()
    assert data.get("user_uploads") is False
    presets = data.get("presets") or []
    assert len(presets) >= 3
    assert presets[0].get("strategy_id")


def test_recommendations_without_scan_flags_no_data(ctx) -> None:
    payload = device_recommendations(
        scanner_db=ctx.databases["scanner"],
        portfolio_db=ctx.portfolio_path,
    )
    assert payload["has_scanner_data"] is False
    assert payload["recommendations"]


def test_recommendations_with_scan_ranks_strategies(ctx) -> None:
    now = datetime(2026, 10, 11, tzinfo=UTC)
    snap = QualifiedSnapshot(
        generated_at=now,
        as_of=now,
        scan_id=1,
        opportunities=[
            OpportunityRow(
                rank=1,
                pair="BTC/USD",
                uniformity=0.8,
                gain_pct=3.0,
                volume_score=1.0,
                entry_signal=True,
            )
        ],
    )
    ScannerStore(ctx.databases["scanner"]).save_snapshot(snap)
    payload = device_recommendations(
        scanner_db=ctx.databases["scanner"],
        portfolio_db=ctx.portfolio_path,
    )
    assert payload["has_scanner_data"] is True
    recs = payload["recommendations"]
    assert recs
    assert recs[0]["score"] >= recs[-1]["score"]
