"""Pure Market Context export helpers for PNG bands."""

from __future__ import annotations

from trendalgo.device import strings as S
from trendalgo.device.market_context_export import (
    buy_pick_cells,
    buy_picks_export_rows,
    coin_context_lines,
    context_is_ok,
)


def test_coin_context_lines_require_ok() -> None:
    assert coin_context_lines({}) == []
    assert not context_is_ok({"ok": False})
    lines = coin_context_lines(
        {
            "ok": True,
            "regime_label": "Ranging",
            "consensus": {"signal": "Buy", "confidence": 70, "score": 1.0},
            "pivots": {"levels": []},
            "risk": {"stop_distance_pct": 1.5, "stop_distance_atr": 1.5, "rr_to_r1": 2.0},
            "structure": {},
        }
    )
    assert lines[0] == S.MARKET_CTX_TITLE
    assert "Buy" in lines[1]


def test_buy_picks_export_rows_rank_ok_contexts() -> None:
    coins = [
        {
            "symbol": "AAA",
            "pair": "AAA/USD",
            "bot_best_net_pct": 10.0,
            "market_context": {
                "ok": True,
                "regime_label": "Ranging",
                "consensus": {"signal": "Buy", "score": 0.5, "confidence": 60},
                "structure": {},
                "risk": {},
            },
        },
        {
            "symbol": "BBB",
            "pair": "BBB/USD",
            "bot_best_net_pct": 40.0,
            "market_context": {
                "ok": True,
                "regime_label": "Trending Up",
                "consensus": {"signal": "Buy", "score": 1.8, "confidence": 90},
                "structure": {"nearest_sr_name": "S1", "confluence": 3},
                "risk": {"rr_to_r1": 2.5},
            },
        },
    ]
    picks = buy_picks_export_rows(coins)
    assert picks[0]["symbol"] == "BBB"
    cells = buy_pick_cells(picks[0])
    assert cells[0] == "BBB/USD"
    assert "Buy" in cells
