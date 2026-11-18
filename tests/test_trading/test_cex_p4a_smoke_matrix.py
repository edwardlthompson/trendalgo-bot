"""CEX-P4a: Tier B trading smoke matrix + Tier C worldwide ack gate."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from trendalgo.trading.control import ExchangeControlStore
from trendalgo.trading.smoke_matrix import (
    TIER_B_IDS,
    TIER_C_IDS,
    run_tier_b_smoke,
    smoke_dry_run,
    smoke_live_refused_without_go_live,
    smoke_tier_c_legal_ack,
)


@pytest.mark.parametrize("exchange_id", TIER_B_IDS)
def test_tier_b_dry_run_smoke(exchange_id: str) -> None:
    result = smoke_dry_run(exchange_id)
    assert result["exchange"] == exchange_id
    assert result["status"] == "simulated"
    assert result["sizing"] == "unpriced_dry_run"


def test_run_tier_b_smoke_matrix(tmp_path: Path) -> None:
    report = run_tier_b_smoke(tmp_path / "control.db")
    assert report["tier"] == "B"
    assert set(report["dry_run"]) == set(TIER_B_IDS)
    for eid in TIER_B_IDS:
        assert report["live_refusal"][eid] == "go_live_required"


@pytest.mark.parametrize("exchange_id", TIER_C_IDS)
def test_tier_c_live_needs_worldwide_ack(
    tmp_path: Path, exchange_id: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("WORLDWIDE_TRADING_ACK", raising=False)
    control = ExchangeControlStore(tmp_path / f"c-{exchange_id}.db")
    reason = smoke_tier_c_legal_ack(control, exchange_id)
    assert "WORLDWIDE_TRADING_ACK" in reason


@pytest.mark.parametrize("exchange_id", TIER_C_IDS)
def test_tier_c_dry_run_ok_without_ack(exchange_id: str, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("WORLDWIDE_TRADING_ACK", raising=False)
    result = smoke_dry_run(exchange_id)
    assert result["status"] == "simulated"
    assert result["us_restricted"] is True


def test_tier_b_live_still_needs_go_live_with_ack(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("WORLDWIDE_TRADING_ACK", "1")
    control = ExchangeControlStore(tmp_path / "tier-b.db")
    reason = smoke_live_refused_without_go_live("gemini", control)
    assert reason == "go_live_required"
    assert os.environ.get("WORLDWIDE_TRADING_ACK") == "1"
