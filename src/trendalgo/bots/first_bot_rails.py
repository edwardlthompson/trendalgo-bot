"""Hard rails for the first live bot — $100 nightmare prevention (Phase 4)."""

from __future__ import annotations

from dataclasses import dataclass

FIRST_BOT_STAKE_USD = 100.0
FIRST_BOT_MAX_OPEN = 1
MAX_ENTRIES_PER_HOUR = 3
MIN_SECONDS_BETWEEN_ENTRY_EXIT = 60
MAX_FEE_PCT_OF_STAKE = 2.0  # reject if round-trip fees exceed this % of stake


@dataclass(frozen=True)
class FirstBotRails:
    stake_cap_usd: float = FIRST_BOT_STAKE_USD
    max_open_trades: int = FIRST_BOT_MAX_OPEN
    max_entries_per_hour: int = MAX_ENTRIES_PER_HOUR
    min_seconds_between_entry_exit: int = MIN_SECONDS_BETWEEN_ENTRY_EXIT
    max_fee_pct_of_stake: float = MAX_FEE_PCT_OF_STAKE
    lifted: bool = False  # user lifted the first-bot cap in Settings


def clamp_first_bot_stake(requested_usd: float, rails: FirstBotRails) -> float:
    if rails.lifted:
        return max(0.0, float(requested_usd))
    return min(max(0.0, float(requested_usd)), rails.stake_cap_usd)


def reject_entry_reason(
    *,
    rails: FirstBotRails,
    open_trades: int,
    entries_last_hour: int,
    seconds_since_last_exit: float | None,
    fee_pct_of_stake: float,
) -> str | None:
    """Return a block reason or None if entry is allowed under first-bot rails."""
    if open_trades >= rails.max_open_trades:
        return "max_open_trades"
    if entries_last_hour >= rails.max_entries_per_hour:
        return "max_entries_per_hour"
    if (
        seconds_since_last_exit is not None
        and seconds_since_last_exit < rails.min_seconds_between_entry_exit
    ):
        return "min_seconds_between_entry_exit"
    if fee_pct_of_stake > rails.max_fee_pct_of_stake:
        return "fees_too_high"
    return None
