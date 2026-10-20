"""Post-sell TF candle cooldown (Phase 4)."""

from __future__ import annotations

from trendalgo.trading.entry_cooldown import CooldownConfig, can_enter, next_candle_open_ms


def test_one_hour_bot_blocks_until_next_candle() -> None:
    sell_open = 1_700_000_000_000  # arbitrary ms aligned as "bar open"
    boundary = next_candle_open_ms(sell_open, "1h")
    assert boundary == sell_open + 3_600_000
    ok, reason = can_enter(
        last_sell_bar_open_ms=sell_open,
        now_ms=sell_open + 1_000,
        config=CooldownConfig(timeframe="1h"),
    )
    assert ok is False
    assert "post_sell_cooldown" in reason
    ok2, _ = can_enter(
        last_sell_bar_open_ms=sell_open,
        now_ms=boundary,
        config=CooldownConfig(timeframe="1h"),
    )
    assert ok2 is True


def test_extra_minutes_lengthens_cooldown() -> None:
    sell_open = 1_700_000_000_000
    cfg = CooldownConfig(timeframe="1h", candle_count=1, extra_minutes=30)
    # Next candle alone would clear at +1h; extra minutes push further.
    ok, _ = can_enter(
        last_sell_bar_open_ms=sell_open,
        now_ms=sell_open + 3_600_000,
        config=cfg,
    )
    assert ok is False
    ok2, _ = can_enter(
        last_sell_bar_open_ms=sell_open,
        now_ms=sell_open + 3_600_000 + 30 * 60 * 1000,
        config=cfg,
    )
    assert ok2 is True
