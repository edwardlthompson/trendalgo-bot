"""SIM-11: decay monitor stub."""

from __future__ import annotations

from trendalgo.botd.decay_monitor import live_trails_fit, maybe_alert


def test_decay_requires_min_trades() -> None:
    assert not live_trails_fit(live_net_pct=1.0, fitted_net_pct=10.0, trades=5)
    assert live_trails_fit(live_net_pct=1.0, fitted_net_pct=10.0, trades=25, margin=2.0)


def test_maybe_alert_emits_when_trailing() -> None:
    alert = maybe_alert(
        bot_id=7, live_net_pct=1.0, fitted_net_pct=10.0, trades=30, margin=2.0
    )
    assert alert is not None
    assert alert.bot_id == 7
    assert maybe_alert(bot_id=7, live_net_pct=9.0, fitted_net_pct=10.0, trades=30, margin=2.0) is None
