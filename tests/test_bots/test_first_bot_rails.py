"""$100 first-bot rails and shadow gate."""

from __future__ import annotations

from trendalgo.bots.first_bot_rails import (
    FIRST_BOT_STAKE_USD,
    FirstBotRails,
    clamp_first_bot_stake,
    reject_entry_reason,
)
from trendalgo.bots.shadow_gate import ShadowProgress, shadow_gate_allows_go_live


def test_clamp_first_bot_stake() -> None:
    rails = FirstBotRails()
    assert clamp_first_bot_stake(500, rails) == FIRST_BOT_STAKE_USD
    assert clamp_first_bot_stake(50, rails) == 50
    assert clamp_first_bot_stake(500, FirstBotRails(lifted=True)) == 500


def test_reject_fee_and_churn() -> None:
    rails = FirstBotRails()
    assert (
        reject_entry_reason(
            rails=rails,
            open_trades=0,
            entries_last_hour=3,
            seconds_since_last_exit=120,
            fee_pct_of_stake=0.5,
        )
        == "max_entries_per_hour"
    )
    assert (
        reject_entry_reason(
            rails=rails,
            open_trades=0,
            entries_last_hour=0,
            seconds_since_last_exit=10,
            fee_pct_of_stake=0.5,
        )
        == "min_seconds_between_entry_exit"
    )
    assert (
        reject_entry_reason(
            rails=rails,
            open_trades=0,
            entries_last_hour=0,
            seconds_since_last_exit=120,
            fee_pct_of_stake=5.0,
        )
        == "fees_too_high"
    )


def test_shadow_gate() -> None:
    incomplete = ShadowProgress(days=1, signals=5)
    assert shadow_gate_allows_go_live(incomplete) == (False, "shadow_incomplete")
    ok, reason = shadow_gate_allows_go_live(incomplete, typed_override="I ACCEPT EARLY GO-LIVE")
    assert ok and reason == "typed_override"
    assert shadow_gate_allows_go_live(ShadowProgress(days=3, signals=0))[0] is True
    assert shadow_gate_allows_go_live(ShadowProgress(days=0, signals=20))[0] is True
