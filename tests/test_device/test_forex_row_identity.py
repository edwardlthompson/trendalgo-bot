"""Forex LTS identity: full pair keys so EUR crosses do not collide."""

from __future__ import annotations

from datetime import UTC, datetime

from trendalgo.device.lts_scan_model import build_lts_rows, load_lts_rows, save_lts_rows
from trendalgo.device.scan_identity import row_key
from trendalgo.scanner.snapshot import OpportunityRow, QualifiedSnapshot


def test_forex_row_key_uses_full_pair() -> None:
    a = {"pair": "EUR/USD", "symbol": "EURUSD", "exchange_id": "forex"}
    b = {"pair": "EUR/GBP", "symbol": "EURGBP", "exchange_id": "forex"}
    assert row_key(a) == "forex:EUR/USD"
    assert row_key(b) == "forex:EUR/GBP"
    assert row_key(a) != row_key(b)


def test_build_lts_rows_forex_unique_symbols() -> None:
    now = datetime.now(tz=UTC)
    snap = QualifiedSnapshot(
        generated_at=now,
        as_of=now,
        scan_id=1,
        degraded=False,
        opportunities=[
            OpportunityRow(
                rank=1,
                pair="EUR/USD",
                uniformity=1.0,
                gain_pct=0.01,
                volume_score=0.0,
                entry_signal=True,
                sparkline=[1.0, 1.1],
            ),
            OpportunityRow(
                rank=2,
                pair="EUR/GBP",
                uniformity=1.0,
                gain_pct=-0.01,
                volume_score=0.0,
                entry_signal=False,
                sparkline=[0.8, 0.9],
            ),
        ],
    )
    rows = build_lts_rows(snap, enrich_charts=False, exchange_id="forex")
    assert [r["symbol"] for r in rows] == ["EURUSD", "EURGBP"]
    assert {row_key(r) for r in rows} == {"forex:EUR/USD", "forex:EUR/GBP"}


def test_save_lts_rows_dedupes_by_row_key(tmp_path: object) -> None:
    from pathlib import Path

    root = Path(tmp_path)
    save_lts_rows(
        root,
        [
            {"pair": "EUR/USD", "symbol": "EURUSD", "exchange_id": "forex"},
            {"pair": "EUR/USD", "symbol": "EURUSD", "exchange_id": "forex", "volume_24h": 9},
            {"pair": "GBP/USD", "symbol": "GBPUSD", "exchange_id": "forex"},
        ],
        lane="forex",
    )
    loaded = load_lts_rows(root, lane="forex")
    assert len(loaded) == 2
    by_pair = {str(r.get("pair")): r for r in loaded}
    assert by_pair["EUR/USD"].get("volume_24h") == 9
