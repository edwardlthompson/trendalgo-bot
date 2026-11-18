"""Sauce product names + create-bot preference."""

from __future__ import annotations

from trendalgo.device.sauce_names import (
    SAUCE_FINAL,
    SAUCE_LAB,
    SAUCE_PEER,
    create_bot_sauce_preference,
    is_sauce,
    is_sauce_final,
    is_sauce_helper,
)


def test_sauce_name_predicates() -> None:
    assert is_sauce(SAUCE_PEER)
    assert is_sauce_helper(SAUCE_PEER)
    assert is_sauce_final(SAUCE_FINAL)
    assert not is_sauce_helper(SAUCE_FINAL)


def test_create_bot_prefers_final() -> None:
    rows = [
        {"indicator": SAUCE_LAB, "net_pct": 12.0, "ss_lab_pending": False},
        {"indicator": SAUCE_FINAL, "net_pct": 9.0, "ss_lab_pending": False},
    ]
    pick = create_bot_sauce_preference(rows)
    assert pick is not None
    assert pick["indicator"] == SAUCE_FINAL


def test_create_bot_falls_back_to_lab() -> None:
    rows = [{"indicator": SAUCE_LAB, "net_pct": 5.0, "ss_lab_pending": False}]
    pick = create_bot_sauce_preference(rows)
    assert pick is not None
    assert pick["indicator"] == SAUCE_LAB
