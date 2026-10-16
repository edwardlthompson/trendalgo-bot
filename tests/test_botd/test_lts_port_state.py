"""p2-lts-port state: JSON round trip and strict refusal of bad host storage (L4)."""

from __future__ import annotations

import json
from typing import Any

import pytest

from trendalgo.botd.lts_port.state import PortState


def _full() -> PortState:
    return PortState(
        bars_seen=42,
        position_qty=2.5,
        entry_price=100.25,
        entry_fee=0.65,
        highest_price=101.5,
        entry_time="2026-09-01 05:00:00+00:00",
        cash=0.0,
        reserve_cash=750.0,
        previous_buy=True,
        exited_on_bar=17,
    )


def test_state_survives_a_json_round_trip_exactly() -> None:
    state = _full()
    restored = PortState.from_dict(json.loads(json.dumps(state.to_dict())))
    assert restored == state
    assert repr(restored.position_qty) == repr(state.position_qty)


def test_an_empty_state_round_trips() -> None:
    assert PortState.from_dict(PortState().to_dict()) == PortState()


def test_integer_numbers_are_accepted_for_money_fields() -> None:
    data = _full().to_dict()
    data["cash"] = 0
    restored = PortState.from_dict(data)
    assert restored.cash == 0.0
    assert isinstance(restored.cash, float)


@pytest.mark.parametrize(
    ("key", "value", "message"),
    [
        ("bars_seen", True, "integer"),
        ("bars_seen", -1, "integer"),
        ("exited_on_bar", "3", "integer"),
        ("cash", float("nan"), "finite number"),
        ("entry_price", "100", "finite number"),
        ("entry_time", 12, "text or null"),
        ("previous_buy", "yes", "true or false"),
    ],
)
def test_wrong_types_are_refused(key: str, value: Any, message: str) -> None:
    data = _full().to_dict()
    data[key] = value
    with pytest.raises(ValueError, match=message):
        PortState.from_dict(data)


def test_missing_and_unknown_keys_are_refused() -> None:
    data = _full().to_dict()
    del data["cash"]
    with pytest.raises(ValueError, match="state keys"):
        PortState.from_dict(data)
    extra = _full().to_dict()
    extra["owner_id"] = "someone"
    with pytest.raises(ValueError, match="state keys"):
        PortState.from_dict(extra)
