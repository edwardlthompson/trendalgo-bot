"""Backtest worker default: eight processes unless the operator overrides it."""

from __future__ import annotations

import pytest

from trendalgo.lts_vendor.shims import config_settings


def test_parallel_workers_default_is_eight(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("BACKTEST_PARALLEL_WORKERS", raising=False)
    assert config_settings._build().backtest_parallel_workers == 8


def test_parallel_workers_env_override_wins(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("BACKTEST_PARALLEL_WORKERS", "3")
    assert config_settings._build().backtest_parallel_workers == 3
