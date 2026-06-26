"""Shared pytest fixtures."""

from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def zero_sync_stagger(monkeypatch: pytest.MonkeyPatch) -> None:
    """Portfolio sync tests must not sleep between exchanges."""
    monkeypatch.setenv("TRENDALGO_SYNC_STAGGER_SEC", "0")
    from trendalgo.exchanges.registry import load_registry

    load_registry.cache_clear()
