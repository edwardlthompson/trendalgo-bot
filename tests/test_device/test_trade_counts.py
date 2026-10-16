"""Win / loss trade count helpers."""

from __future__ import annotations

from trendalgo.device.trade_counts import wins_losses


def test_wins_losses_from_win_pct() -> None:
    wins, losses = wins_losses({"trades": 10, "win_pct": 60.0})
    assert wins == 6 and losses == 4


def test_wins_losses_bh_dash() -> None:
    assert wins_losses({"trades": "-"}) == (None, None)
