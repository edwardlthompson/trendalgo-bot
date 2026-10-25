"""Market Context pane states (dedicated band, not strategy table)."""

from __future__ import annotations

from trendalgo.device.views.market_context_format import risk_line, signal_line
from trendalgo.device.views.market_context_pane import MarketContextPane


def test_format_signal_and_risk() -> None:
    ctx = {
        "ok": True,
        "regime_label": "Trending Up",
        "consensus": {"signal": "Buy", "confidence": 62.0},
        "risk": {
            "stop_distance_pct": 1.5,
            "stop_distance_atr": 1.5,
            "rr_to_r1": 2.0,
            "rr_to_r2": 3.5,
        },
    }
    assert "Buy" in signal_line(ctx)
    assert "Trending Up" in signal_line(ctx)
    assert "R1" in risk_line(ctx)


def test_pane_empty_loading_context(qtbot) -> None:  # type: ignore[no-untyped-def]
    pane = MarketContextPane()
    qtbot.addWidget(pane)
    pane.set_empty()
    pane.set_loading()
    pane.set_context(
        {
            "ok": True,
            "last_price": 100.0,
            "regime_label": "Ranging",
            "consensus": {"signal": "Neutral", "confidence": 10.0, "score": 0.0, "votes": {}},
            "pivots": {
                "levels": [
                    {"name": "PP", "price": 100.0, "strength": 40.0},
                    {"name": "R1", "price": 102.0, "strength": 30.0},
                    {"name": "S1", "price": 98.0, "strength": 35.0},
                ]
            },
            "risk": {
                "stop_distance_pct": 2.0,
                "stop_distance_atr": 1.5,
                "rr_to_r1": 1.2,
                "rr_to_r2": None,
            },
            "structure": {
                "volume_ok": False,
                "confluence": 1,
                "nearest_sr_name": "S1",
                "nearest_sr_pct": 0.5,
                "nearest_sr_atr": 0.3,
                "vwap_dist_pct": -0.4,
                "poc": 101.0,
                "drawdown_from_high_pct": -2.0,
            },
        }
    )
    assert not pane._row.isHidden()  # noqa: SLF001 — equal-width module row
    assert len(pane._modules) == 4  # noqa: SLF001
