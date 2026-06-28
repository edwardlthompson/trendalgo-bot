"""Bot capacity guardrails."""

from __future__ import annotations

import pytest

from trendalgo.bots.limits import (
    MAX_BOTS_TOTAL,
    chart_lookback_seconds,
    max_ohlcv_bars,
    validate_bot_capacity,
)


def test_chart_lookback_shorter_for_1s() -> None:
    assert chart_lookback_seconds("1S") == 3_600
    assert chart_lookback_seconds("60") == 30 * 86_400
    assert max_ohlcv_bars("1S") == 3_600


def test_rejects_when_total_bots_exceeded() -> None:
    bots = [{"id": i, "enabled": False, "timeframe": "60"} for i in range(MAX_BOTS_TOTAL)]
    with pytest.raises(ValueError, match="Bot limit reached"):
        validate_bot_capacity(bots, paper=True, adding=True)


def test_rejects_second_1s_enabled_bot() -> None:
    bots = [{"id": 1, "enabled": True, "timeframe": "1S"}]
    with pytest.raises(ValueError, match="1-second"):
        validate_bot_capacity(bots, paper=True, enabling=True, timeframe="1S")


def test_allows_many_disabled_bots() -> None:
    bots = [{"id": i, "enabled": False, "timeframe": "1S"} for i in range(100)]
    validate_bot_capacity(bots, paper=True, adding=True, enabling=False, timeframe="1S")


def test_allows_adding_disabled_sub_minute_bot() -> None:
    bots = [{"id": 1, "enabled": True, "timeframe": "1S"}]
    validate_bot_capacity(bots, paper=True, adding=True, enabling=False, timeframe="1S")
