"""SIM-07: fee drag, exposure, excess vs hold; reject high fee drag."""

from __future__ import annotations

from trendalgo.backtest.secret_sauce_lab.search_metrics import enrich_trial_stats


def test_enrich_rejects_fee_drag_above_35() -> None:
    stats = {"gross_profit": 100.0, "fees_paid": 40.0, "net_profit": 60.0, "trades": 5}
    out = enrich_trial_stats(stats, stake_usd=1000.0, bh_net=10.0, n_bars=100)
    assert out["fee_drag_pct"] == 0.4
    assert out["reject_reason"] == "fee_drag:0.40"
    assert out["exposure_pct"] == 10.0
    assert out["excess_vs_bh"] == 50.0
    assert "net_pct" in out


def test_enrich_keeps_low_drag() -> None:
    stats = {"gross_profit": 100.0, "fees_paid": 10.0, "net_profit": 90.0, "trades": 3}
    out = enrich_trial_stats(stats, stake_usd=1000.0, bh_net=0.0, n_bars=50)
    assert out["reject_reason"] is None
    assert out["fee_drag_pct"] == 0.1
