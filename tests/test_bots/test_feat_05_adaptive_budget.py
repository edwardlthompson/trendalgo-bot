"""FEAT-05: adaptive bot budgeting vs static MAX_ENABLED_BOTS_PAPER."""

from __future__ import annotations

from trendalgo.bots.limits import (
    ADAPTIVE_PAPER_FLOOR,
    MAX_ENABLED_BOTS_LIVE,
    MAX_ENABLED_BOTS_PAPER,
    adaptive_max_enabled_bots,
    validate_bot_capacity,
)


def test_adaptive_paper_scales_below_static_ceiling() -> None:
    n = adaptive_max_enabled_bots(paper=True, cpu_count=1, api_budget_per_min=10)
    assert ADAPTIVE_PAPER_FLOOR <= n < MAX_ENABLED_BOTS_PAPER
    assert n == 5  # api 10 // 2


def test_adaptive_live_keeps_static() -> None:
    assert (
        adaptive_max_enabled_bots(paper=False, cpu_count=64, api_budget_per_min=1000)
        == MAX_ENABLED_BOTS_LIVE
    )


def test_validate_uses_override() -> None:
    bots = [{"id": i, "enabled": True, "timeframe": "60"} for i in range(5)]
    validate_bot_capacity(bots, paper=True, enabling=True, max_enabled_override=10)
    try:
        validate_bot_capacity(bots, paper=True, enabling=True, max_enabled_override=5)
        raised = False
    except ValueError:
        raised = True
    assert raised
