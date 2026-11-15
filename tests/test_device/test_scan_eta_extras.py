"""ETA includes Market Context and Sauce Pan add-ons."""

from __future__ import annotations

from trendalgo.device.scan_time_history import (
    ScanTimeHistory,
    estimate_label,
    estimate_scan_seconds,
)


def test_estimate_includes_mc_and_sauce_costs() -> None:
    hist = ScanTimeHistory(mean_mc_s=1.0, mean_sauce_s=40.0, mean_per_strat_tf_s=0.1)
    catalog, mc, sauce, total = estimate_scan_seconds(
        hist,
        n_strategies=10,
        n_timeframes=12,
        had_subhour=False,
        n_coins=50,
        market_context=True,
        sauce_with_scan=True,
        sauce_top_n=10,
    )
    assert mc == 50.0
    assert sauce == 400.0
    assert total == catalog + mc + sauce
    label = estimate_label(
        hist,
        n_strategies=10,
        n_timeframes=12,
        had_subhour=False,
        n_coins=50,
        market_context=True,
        sauce_with_scan=True,
        sauce_top_n=10,
    )
    assert "MC" in label
    assert "Sauce" in label


def test_estimate_skips_mc_and_sauce_when_off() -> None:
    hist = ScanTimeHistory(mean_mc_s=1.0, mean_sauce_s=40.0)
    _c, mc, sauce, _t = estimate_scan_seconds(
        hist,
        n_strategies=5,
        n_timeframes=6,
        had_subhour=False,
        n_coins=20,
        market_context=False,
        sauce_with_scan=False,
        sauce_top_n=10,
    )
    assert mc == 0.0
    assert sauce == 0.0
    label = estimate_label(
        hist,
        n_strategies=5,
        n_timeframes=6,
        had_subhour=False,
        n_coins=20,
        market_context=False,
        sauce_with_scan=False,
    )
    assert "MC off" in label
    assert "Sauce off" in label
