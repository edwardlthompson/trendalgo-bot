"""AV-G-BRD5 — spectrum frac + buy-pick row keys match PySide BuyPicksPane."""

from __future__ import annotations

import pytest

pytest.importorskip("PySide6")

from trendalgo.device.buy_picks import rank_buy_picks  # noqa: E402
from trendalgo.device.views.market_context_gfx import BUY_THRESHOLD, score_to_frac  # noqa: E402


def _spectrum_tick_x(width: float, score: float, *, margin: float = 2.0) -> float:
    track_w = max(1.0, width - 2 * margin)
    return margin + score_to_frac(score) * track_w


def test_score_to_frac_bounds() -> None:
    assert score_to_frac(-2.0) == 0.0
    assert score_to_frac(2.0) == 1.0
    assert score_to_frac(0.0) == 0.5
    assert abs(score_to_frac(BUY_THRESHOLD) - (BUY_THRESHOLD + 2.0) / 4.0) < 1e-9


def test_spectrum_tick_monotonic() -> None:
    w = 124.0
    assert _spectrum_tick_x(w, -1.0) < _spectrum_tick_x(w, 0.0) < _spectrum_tick_x(w, BUY_THRESHOLD)


def test_rank_buy_picks_exposes_nine_col_fields() -> None:
    coins = [
        {
            "symbol": "btc",
            "pair": "BTC/USD",
            "bot_best_net_pct": 12.5,
            "bot_best_label": "RSI",
            "market_context": {
                "ok": True,
                "regime_label": "trend",
                "consensus": {"signal": "Buy", "score": 1.2, "confidence": 80},
                "structure": {"nearest_sr_name": "S1", "confluence": 3},
                "risk": {"rr_to_r1": 1.8},
            },
        }
    ]
    rows = rank_buy_picks(coins)
    assert len(rows) == 1
    row = rows[0]
    for key in (
        "pair",
        "signal",
        "score",
        "confidence",
        "nearest_sr",
        "rr_r1",
        "confluence",
        "bot_best_net_pct",
        "bot_best_label",
    ):
        assert key in row
