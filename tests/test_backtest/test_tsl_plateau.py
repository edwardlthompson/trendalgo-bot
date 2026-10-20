"""Plateau pick: most profitable TSL, then lowest safe +1% breath."""

from __future__ import annotations

from trendalgo.backtest.tsl_plateau import pick_tsl_from_grid


def _trial(tsl: float, net: float, *, hits: int = 0, trades: int = 5) -> dict:
    return {
        "trailing_stop_pct": tsl,
        "net_profit": net,
        "tsl_hits": hits,
        "trades": trades,
        "wins": 3,
    }


def test_plateau_lowest_plus_breath() -> None:
    """Equal nets for 8–20% (unhit) → assign 9% (8+1)."""
    trials = [_trial(i / 100.0, 50.0, hits=0) for i in range(1, 21)]
    # Narrower stops hit and score worse.
    for i in range(1, 8):
        trials[i - 1] = _trial(i / 100.0, 40.0, hits=2)
    picked = pick_tsl_from_grid(trials, signal_net=50.0)
    assert picked is not None
    assert float(picked["trailing_stop_pct"]) == 0.09
    assert picked.get("tsl_breath") is True


def test_unique_most_profitable_no_forced_widen() -> None:
    """5% uniquely best with hits → keep 5% (breath would leave the plateau)."""
    trials = [_trial(i / 100.0, 10.0, hits=1) for i in range(1, 21)]
    trials[4] = _trial(0.05, 99.0, hits=3)
    picked = pick_tsl_from_grid(trials, signal_net=10.0)
    assert picked is not None
    assert float(picked["trailing_stop_pct"]) == 0.05


def test_signal_strictly_best_unhit_plateau() -> None:
    """Signal best; unhit trails 12–20% match → assign 13%."""
    trials = []
    for i in range(1, 21):
        tsl = i / 100.0
        if i < 12:
            trials.append(_trial(tsl, 80.0, hits=2))
        else:
            trials.append(_trial(tsl, 100.0, hits=0))
    picked = pick_tsl_from_grid(trials, signal_net=100.0)
    assert picked is not None
    assert float(picked["trailing_stop_pct"]) == 0.13
