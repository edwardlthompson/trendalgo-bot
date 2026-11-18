"""FEAT-03: fee-aware routing prefers maker when tolerated."""

from __future__ import annotations

from trendalgo.trading.fee_routing import FeeTier, prefer_maker_when_tolerated


def test_prefer_maker_when_resting_ok_and_cheaper() -> None:
    tiers = FeeTier(maker_pct=0.001, taker_pct=0.0026)
    decision = prefer_maker_when_tolerated(
        tiers, resting_entry_ok=True, max_maker_wait_bars=3, urgency_bars=1
    )
    assert decision.style == "maker"
    assert decision.expected_fee_pct == 0.001


def test_taker_when_resting_not_tolerated() -> None:
    tiers = FeeTier(maker_pct=0.0, taker_pct=0.0026)
    decision = prefer_maker_when_tolerated(tiers, resting_entry_ok=False)
    assert decision.style == "taker"
    assert decision.reason == "resting_not_tolerated"


def test_taker_when_urgency_exceeds_wait() -> None:
    tiers = FeeTier(maker_pct=0.001, taker_pct=0.0026)
    decision = prefer_maker_when_tolerated(
        tiers, resting_entry_ok=True, max_maker_wait_bars=1, urgency_bars=3
    )
    assert decision.style == "taker"
    assert decision.reason == "urgency_exceeds_wait"
