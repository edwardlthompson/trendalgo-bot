"""FEAT-02: generic shadow-to-live promotion gate for any strategy."""

from __future__ import annotations

from trendalgo.botd.shadow_gate import StrategyShadowState, promotion_allowed


def test_any_strategy_blocked_until_shadow() -> None:
    state = StrategyShadowState(strategy_id="plan:abc", days=1.0, signals=5)
    assert promotion_allowed(state) == (False, "shadow_incomplete")
    ok, reason = promotion_allowed(state, typed_override="I ACCEPT EARLY GO-LIVE")
    assert ok and reason == "typed_override"


def test_passed_shadow_still_needs_clean_divergence() -> None:
    dirty = StrategyShadowState(strategy_id="bot:7", days=5.0, signals=30, divergence_clean=False)
    assert promotion_allowed(dirty) == (False, "shadow_divergence")
    clean = StrategyShadowState(strategy_id="bot:7", days=5.0, signals=30, divergence_clean=True)
    assert promotion_allowed(clean) == (True, "shadow_ok")


def test_signals_alone_can_clear_gate() -> None:
    state = StrategyShadowState(strategy_id="sauce:rsi", days=0.0, signals=20)
    assert promotion_allowed(state)[0] is True
