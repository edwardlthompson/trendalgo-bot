"""Apply first-bot stake clamp at go-live / live sizing time (Phase 4)."""

from __future__ import annotations

from trendalgo.bots.first_bot_rails import FirstBotRails, clamp_first_bot_stake
from trendalgo.device.execution_venue import load_execution_venue
from trendalgo.device.profile import profile_dir


def live_stake_usd(requested_usd: float, *, rails: FirstBotRails | None = None) -> float:
    """Clamp stake for live unless the user lifted first-bot rails in Settings."""
    if rails is None:
        settings = load_execution_venue(profile_dir())
        rails = FirstBotRails(lifted=settings.first_bot_rails_lifted)
    return clamp_first_bot_stake(requested_usd, rails)
