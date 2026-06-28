"""Tests for exchange fee schedules."""

from pathlib import Path

import pytest

from trendalgo.exchanges import fees
from trendalgo.exchanges.fee_store import FeeStore, reset_fee_store


@pytest.fixture
def seeded_fees(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> FeeStore:
    monkeypatch.setenv("TRENDALGO_DATA_DIR", str(tmp_path))
    reset_fee_store()
    fees.clear_fee_cache()
    store = FeeStore(tmp_path / "exchange_fees.db")
    store.seed_from_json()
    reset_fee_store()
    fees.clear_fee_cache()
    return store


def test_get_fee_schedule_kraken(seeded_fees: FeeStore) -> None:
    fee = fees.get_fee_schedule("kraken")
    assert fee.exchange_id == "kraken"
    assert fee.taker_pct == 0.0026
    assert fee.maker_pct == 0.0016
    assert fee.tier == "retail_default"


def test_round_trip_taker_cost(seeded_fees: FeeStore) -> None:
    fee = fees.get_fee_schedule("kraken")
    cost = fee.round_trip_taker_cost(1000.0)
    assert cost == fees.round_trip_taker_cost(1000.0, fee.taker_pct)
    assert cost == 5.2


def test_all_fee_schedules_non_empty(seeded_fees: FeeStore) -> None:
    schedules = fees.all_fee_schedules()
    assert len(schedules) >= 5
    ids = {s.exchange_id for s in schedules}
    assert "kraken" in ids
