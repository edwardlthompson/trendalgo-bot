"""Win / loss trade count helpers."""

from __future__ import annotations

from trendalgo.device.trade_counts import win_pct, wins_losses


def test_wins_losses_from_win_pct() -> None:
    wins, losses = wins_losses({"trades": 10, "win_pct": 60.0})
    assert wins == 6 and losses == 4


def test_wins_losses_bh_dash() -> None:
    assert wins_losses({"trades": "-"}) == (None, None)


def test_win_pct_derives_when_stored_as_dash() -> None:
    """Secret Sauce TA rows often store win_pct='-' with wins/trades filled."""
    assert win_pct({"trades": 8, "wins": 5, "open_trades": 0, "win_pct": "-"}) == 62.5
    assert win_pct({"trades": 8, "wins": 5, "win_pct": 62.5}) == 62.5
