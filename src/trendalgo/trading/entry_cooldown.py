"""Post-sell re-entry cooldown: at least one candle of the bot TF (Phase 4)."""

from __future__ import annotations

from dataclasses import dataclass

from trendalgo.constants.timeframes import ccxt_interval_seconds, timeframe_for_fetch


@dataclass(frozen=True)
class CooldownConfig:
    """Floor is one TF candle; optional extra minutes lengthen further."""

    timeframe: str = "1h"
    candle_count: int = 1
    extra_minutes: int = 0

    def duration_seconds(self) -> int:
        step = ccxt_interval_seconds(timeframe_for_fetch(self.timeframe))
        candles = max(1, int(self.candle_count))
        extra = max(0, int(self.extra_minutes)) * 60
        return candles * step + extra


def next_candle_open_ms(sell_bar_open_ms: int, timeframe: str) -> int:
    """Earliest ms when a new entry is allowed after a sell on sell_bar_open_ms."""
    step_ms = ccxt_interval_seconds(timeframe_for_fetch(timeframe)) * 1000
    return int(sell_bar_open_ms) + step_ms


def entry_blocked_until_ms(
    *,
    last_sell_bar_open_ms: int | None,
    now_ms: int,
    config: CooldownConfig,
) -> int | None:
    """Return the timestamp until which entries are blocked, or None if clear."""
    if last_sell_bar_open_ms is None:
        return None
    # Default: wait until the next candle after the sell bar has opened.
    boundary = next_candle_open_ms(last_sell_bar_open_ms, config.timeframe)
    # Longer override: absolute duration from sell bar open.
    absolute = int(last_sell_bar_open_ms) + config.duration_seconds() * 1000
    until = max(boundary, absolute)
    if now_ms >= until:
        return None
    return until


def can_enter(
    *,
    last_sell_bar_open_ms: int | None,
    now_ms: int,
    config: CooldownConfig,
) -> tuple[bool, str]:
    until = entry_blocked_until_ms(
        last_sell_bar_open_ms=last_sell_bar_open_ms, now_ms=now_ms, config=config
    )
    if until is None:
        return True, "ok"
    return False, f"post_sell_cooldown_until_ms={until}"
