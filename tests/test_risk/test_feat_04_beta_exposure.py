"""FEAT-04: beta-weighted exposure cap."""

from __future__ import annotations

from trendalgo.risk.beta_exposure import PositionBeta, beta_exposure_error, beta_weighted_exposure


def test_correlated_longs_consume_beta_budget() -> None:
    positions = [
        PositionBeta("BTC/USD", 1000.0, 1.0),
        PositionBeta("ETH/USD", 1000.0, 0.9),
    ]
    assert beta_weighted_exposure(positions) == 1900.0
    err = beta_exposure_error(positions, equity_usd=2000.0, max_beta_exposure=0.8)
    assert err is not None
    assert "exceeds" in err


def test_within_cap_ok() -> None:
    positions = [PositionBeta("BTC/USD", 500.0, 1.0)]
    assert beta_exposure_error(positions, equity_usd=2000.0, max_beta_exposure=0.5) is None
