"""High-core worker auto-caps."""

from __future__ import annotations

import pytest

from trendalgo.device import scan_parallel as sp


def test_all_ta_coin_workers_cap_and_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("TRENDALGO_ALL_TA_WORKERS", raising=False)
    monkeypatch.setattr(sp, "cpu_budget", lambda: 31)
    assert sp.all_ta_coin_workers() == 10
    monkeypatch.setenv("TRENDALGO_ALL_TA_WORKERS", "8")
    assert sp.all_ta_coin_workers() == 8


def test_pass2_workers_env_max(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TRENDALGO_PASS2_WORKERS", "20")
    assert sp.pass2_worker_count() == 20
    monkeypatch.setenv("TRENDALGO_PASS2_WORKERS", "99")
    assert sp.pass2_worker_count() == 24
