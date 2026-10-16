"""Plan stake modes and in-place edit validation."""

from __future__ import annotations

from trendalgo.device.plan_model import (
    STAKE_FIXED,
    STAKE_PERCENT,
    check_plan,
    validate_bot,
)


def test_validate_bot_accepts_equity_percent() -> None:
    spec, errors = validate_bot(
        name="Alpha",
        pair="BTC/USD",
        timeframe="1h",
        indicator="RSI",
        stake="10",
        trailing_stop="5",
        stake_mode=STAKE_PERCENT,
    )
    assert errors == []
    assert spec is not None
    assert spec.stake_mode == STAKE_PERCENT
    assert spec.equity_pct == 10.0
    assert spec.stake_usd == 0.0


def test_validate_bot_rejects_percent_over_100() -> None:
    spec, errors = validate_bot(
        name="Alpha",
        pair="BTC/USD",
        timeframe="1h",
        indicator="RSI",
        stake="150",
        trailing_stop="5",
        stake_mode=STAKE_PERCENT,
    )
    assert spec is None
    assert any("percent" in message.lower() for message in errors)


def test_fixed_usd_still_works() -> None:
    spec, errors = validate_bot(
        name="Alpha",
        pair="BTC/USD",
        timeframe="4h",
        indicator="RSI",
        stake="100",
        trailing_stop="0",
        stake_mode=STAKE_FIXED,
    )
    assert errors == []
    assert spec is not None
    assert check_plan([spec]) == []
