"""Tests for exchange fee SQLite store."""

from pathlib import Path

from trendalgo.exchanges.fee_store import FeeStore


def test_fee_store_seed_and_checks(tmp_path: Path) -> None:
    store = FeeStore(tmp_path / "fees.db")
    assert store.count() == 0
    seeded = store.seed_from_json()
    assert seeded >= 5
    assert store.count() >= 5
    kraken = store.get("kraken")
    assert kraken is not None
    assert kraken["taker_pct"] == 0.0026
    checks = store.recent_checks(limit=5)
    assert checks
    assert store.last_global_check() is not None

    store.upsert(
        "kraken",
        ccxt_id="kraken",
        taker_pct=0.003,
        maker_pct=0.0016,
        tier="retail_default",
        source="ccxt",
    )
    store.record_check(
        "kraken",
        "updated",
        prev_taker=0.0026,
        prev_maker=0.0016,
        new_taker=0.003,
        new_maker=0.0016,
    )
    updated = store.get("kraken")
    assert updated is not None
    assert updated["source"] == "ccxt"
    assert updated["taker_pct"] == 0.003
