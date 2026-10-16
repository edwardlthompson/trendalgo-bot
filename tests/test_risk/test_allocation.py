"""R4: the bots' equity caps must fit host equity times the max exposure."""

from __future__ import annotations

from trendalgo.risk.allocation import allocation_error


def test_an_over_cap_plan_is_rejected() -> None:
    reason = allocation_error([4000, 3000], host_equity_usd=5000, max_exposure_pct=0.8)
    assert reason is not None
    assert "allocation rejected" in reason


def test_a_plan_inside_the_cap_passes() -> None:
    assert allocation_error([2000, 1500], host_equity_usd=5000, max_exposure_pct=0.8) is None


def test_an_empty_plan_passes() -> None:
    assert allocation_error([], host_equity_usd=5000, max_exposure_pct=0.8) is None


def test_negative_or_nan_caps_are_rejected() -> None:
    negative = allocation_error([-1.0], host_equity_usd=5000, max_exposure_pct=0.8)
    assert negative is not None and "not a number" in negative
    assert allocation_error([float("nan")], host_equity_usd=5000, max_exposure_pct=0.8)
