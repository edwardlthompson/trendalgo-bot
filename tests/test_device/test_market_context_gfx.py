"""Market Context glance graphics paint + gauge zone alignment."""

from __future__ import annotations

from trendalgo.device.views.buy_picks_gfx import ScoreSpectrum, spectrum_tick_x
from trendalgo.device.views.market_context_gfx import (
    BUY_THRESHOLD,
    LevelsLadder,
    RiskBars,
    SignalGauge,
    StructureMeters,
    score_to_deg,
    zone_for_score,
)


def test_gfx_widgets_paint(qtbot) -> None:
    raw = {
        "ok": True,
        "last_price": 100.0,
        "consensus": {"signal": "Buy", "confidence": 62.0, "score": 1.2},
        "pivots": {
            "levels": [
                {"name": "R1", "price": 105.0},
                {"name": "P", "price": 100.0},
                {"name": "S1", "price": 95.0},
            ]
        },
        "risk": {"rr_to_r1": 2.1, "rr_to_r2": 3.4},
        "structure": {
            "vwap_dist_pct": -0.4,
            "poc": 102.0,
            "drawdown_from_high_pct": -3.2,
        },
    }
    widgets = (SignalGauge(), LevelsLadder(), RiskBars(), StructureMeters())
    for w in widgets:
        qtbot.addWidget(w)
        w.resize(160, 80)
        w.set_data(raw)
        w.show()
        qtbot.waitExposed(w)
        w.repaint()


def test_buy_threshold_needle_in_buy_zone() -> None:
    buy_lo = score_to_deg(2.0)
    buy_hi = score_to_deg(BUY_THRESHOLD)
    needle = score_to_deg(BUY_THRESHOLD)
    assert buy_lo <= needle <= buy_hi
    assert zone_for_score(BUY_THRESHOLD) == "Buy"
    assert zone_for_score(0.0) == "Neutral"
    assert zone_for_score(-BUY_THRESHOLD) == "Sell"


def test_spectrum_tick_monotonic() -> None:
    w = 120.0
    x_neg = spectrum_tick_x(w, -1.0)
    x_zero = spectrum_tick_x(w, 0.0)
    x_pos = spectrum_tick_x(w, BUY_THRESHOLD)
    assert x_neg < x_zero < x_pos


def test_score_spectrum_paints(qtbot) -> None:
    spec = ScoreSpectrum()
    qtbot.addWidget(spec)
    spec.resize(140, 18)
    spec.set_score(BUY_THRESHOLD)
    spec.show()
    qtbot.waitExposed(spec)
    spec.repaint()
