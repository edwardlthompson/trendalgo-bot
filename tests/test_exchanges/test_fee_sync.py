"""Tests for exchange fee sync."""

from pathlib import Path
from unittest.mock import patch

from trendalgo.exchanges.fee_store import FeeStore
from trendalgo.exchanges.fee_sync import fees_differ, sync_exchange_fees
from trendalgo.exchanges.fee_website import FetchedFees


def test_fees_differ_epsilon() -> None:
    assert not fees_differ(0.0026, 0.0026)
    assert fees_differ(0.0026, 0.003)


def test_sync_updates_changed_fees(tmp_path: Path) -> None:
    store = FeeStore(tmp_path / "fees.db")
    store.seed_from_json()

    def fake_fetch(exchange_id: str, seed: dict) -> FetchedFees:
        if exchange_id == "kraken":
            return FetchedFees(
                taker_pct=0.003,
                maker_pct=0.0016,
                source="website",
                source_url=str(seed.get("source_url", "")),
                verified=True,
            )
        from trendalgo.exchanges.fee_fetcher import fetch_exchange_fees

        return fetch_exchange_fees(exchange_id, seed)

    with patch("trendalgo.exchanges.fee_sync.fetch_exchange_fees", side_effect=fake_fetch):
        summary = sync_exchange_fees(store)

    assert "kraken" in summary["updated"]
    row = store.get("kraken")
    assert row is not None
    assert row["taker_pct"] == 0.003
    assert row["source"] == "website"
