"""Shared All-TA coin × pass2 CPU budget."""

from __future__ import annotations

import os
from typing import Any

from trendalgo.device.scan_parallel import (
    all_ta_coin_workers,
    cpu_budget,
    pass2_worker_count,
    set_coin_parallel,
)


def test_pass2_splits_budget_by_coin_parallel(monkeypatch: Any) -> None:
    monkeypatch.setattr("trendalgo.device.scan_parallel.cpu_budget", lambda: 12)
    monkeypatch.delenv("TRENDALGO_PASS2_WORKERS", raising=False)
    set_coin_parallel(4)
    try:
        assert pass2_worker_count() == 3
        set_coin_parallel(1)
        assert pass2_worker_count() == 12
    finally:
        set_coin_parallel(1)


def test_env_overrides_workers(monkeypatch: Any) -> None:
    monkeypatch.setenv("TRENDALGO_ALL_TA_WORKERS", "5")
    monkeypatch.setenv("TRENDALGO_PASS2_WORKERS", "7")
    set_coin_parallel(4)
    try:
        assert all_ta_coin_workers() == 5
        assert pass2_worker_count() == 7
    finally:
        set_coin_parallel(1)
        monkeypatch.delenv("TRENDALGO_ALL_TA_WORKERS", raising=False)
        monkeypatch.delenv("TRENDALGO_PASS2_WORKERS", raising=False)


def test_cpu_budget_leaves_one_core() -> None:
    n = os.cpu_count() or 4
    assert cpu_budget() == max(1, n - 1)


def test_all_ta_coin_workers_capped_at_six(monkeypatch: Any) -> None:
    monkeypatch.delenv("TRENDALGO_ALL_TA_WORKERS", raising=False)
    monkeypatch.setattr("trendalgo.device.scan_parallel.cpu_budget", lambda: 30)
    assert all_ta_coin_workers() == 6
