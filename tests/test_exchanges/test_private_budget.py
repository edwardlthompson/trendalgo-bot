"""Per-venue private RateBudget (Phase 1b)."""

from __future__ import annotations

import pytest

from trendalgo.exchanges.private_budget import (
    acquire_private_slot,
    call_private,
    reset_budgets,
)
from trendalgo.exchanges.registry import load_registry


def setup_function() -> None:
    reset_budgets()
    load_registry.cache_clear()


def test_budget_exhausts() -> None:
    assert acquire_private_slot("kraken", max_per_min=2)
    assert acquire_private_slot("kraken", max_per_min=2)
    assert acquire_private_slot("kraken", max_per_min=2) is False


def test_call_private_refuses_when_exhausted() -> None:
    acquire_private_slot("kraken", max_per_min=1)
    with pytest.raises(RuntimeError, match="private_rate_budget_exhausted"):
        call_private("kraken", lambda: "x", max_per_min=1)


def test_registry_has_rate_floors() -> None:
    entry = load_registry().by_id("kraken")
    assert entry is not None
    assert entry.min_sync_interval_sec == 15
    assert entry.max_private_calls_per_min == 15
