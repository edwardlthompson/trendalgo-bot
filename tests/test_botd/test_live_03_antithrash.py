"""LIVE-03: dwell, one quantile step, hysteresis; flat noise no churn 30d."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from trendalgo.botd.retune_antithrash import (
    AntiThrashConfig,
    apply_antithrash,
    simulate_flat_noise_churn,
)


def test_dwell_and_one_quantile_step() -> None:
    cfg = AntiThrashConfig()
    last = datetime(2026, 11, 1, 6, 0, tzinfo=UTC)
    now = last + timedelta(days=1)  # < 3 day dwell
    out = apply_antithrash(
        incumbent={"q": 0.5},
        proposed={"q": 0.7},
        incumbent_net=1.0,
        proposed_net=1.5,
        last_change_utc=last,
        now_utc=now,
        config=cfg,
    )
    assert out.accepted is False
    assert out.reason == "dwell"
    now2 = last + timedelta(days=3)
    out2 = apply_antithrash(
        incumbent={"q": 0.5},
        proposed={"q": 0.9},  # two quantile steps away if step=0.1
        incumbent_net=1.0,
        proposed_net=2.0,
        last_change_utc=last,
        now_utc=now2,
        config=cfg,
        quantiles={"q": [0.4, 0.5, 0.6, 0.7, 0.8, 0.9]},
    )
    assert out2.accepted is True
    assert out2.params["q"] == 0.6  # one step only


def test_hysteresis_blocks_tiny_diff() -> None:
    cfg = AntiThrashConfig(hysteresis_pct=0.3)
    now = datetime(2026, 11, 11, 6, 0, tzinfo=UTC)
    out = apply_antithrash(
        incumbent={"q": 0.5},
        proposed={"q": 0.6},
        incumbent_net=1.0,
        proposed_net=1.2,  # 0.2% < 0.3% band
        last_change_utc=now - timedelta(days=5),
        now_utc=now,
        config=cfg,
        quantiles={"q": [0.5, 0.6]},
    )
    assert out.accepted is False
    assert out.reason == "hysteresis"


def test_noisy_flat_series_no_churn_30d() -> None:
    changes = simulate_flat_noise_churn(days=30, noise_pct=0.25, seed=7)
    assert changes == 0
