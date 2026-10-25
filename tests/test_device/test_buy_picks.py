"""Buy picks / Market Context top-10 ranking."""

from __future__ import annotations

from typing import Any

from trendalgo.device.buy_picks import rank_buy_picks


def _coin(
    *,
    symbol: str,
    signal: str = "Buy",
    score: float = 1.0,
    confidence: float = 50.0,
    nearest: str = "S1",
    confluence: int = 0,
    rr: float | None = 2.0,
    volume_ok: bool = True,
    dd: float | None = -3.0,
    best: float | None = 5.0,
    label: str = "MFI 3h",
    ok: bool = True,
) -> dict[str, Any]:
    return {
        "symbol": symbol,
        "pair": f"{symbol}/USD",
        "bot_best_net_pct": best,
        "bot_best_label": label,
        "market_context": {
            "ok": ok,
            "regime_label": "Trending Up",
            "consensus": {"signal": signal, "score": score, "confidence": confidence},
            "risk": {"rr_to_r1": rr},
            "structure": {
                "nearest_sr_name": nearest,
                "confluence": confluence,
                "volume_ok": volume_ok,
                "drawdown_from_high_pct": dd,
            },
        },
    }


def test_always_ranks_by_score_including_non_buys() -> None:
    coins = [
        _coin(symbol="ETH", signal="Buy", score=0.5, best=10.0),
        _coin(symbol="BTC", signal="Neutral", score=1.2, best=4.0),
        _coin(symbol="SOL", signal="Sell", score=0.9, best=8.0),
    ]
    picks = rank_buy_picks(coins)
    assert [p["symbol"] for p in picks] == ["BTC", "SOL", "ETH"]


def test_caps_at_ten() -> None:
    coins = [_coin(symbol=f"C{i}", signal="Neutral", score=float(i) / 10.0) for i in range(15)]
    picks = rank_buy_picks(coins)
    assert len(picks) == 10
    assert picks[0]["symbol"] == "C14"


def test_skips_missing_context() -> None:
    coins = [
        _coin(symbol="A", ok=False, score=2.0),
        _coin(symbol="B", score=0.4),
    ]
    picks = rank_buy_picks(coins)
    assert [p["symbol"] for p in picks] == ["B"]


def test_missing_ta_still_included() -> None:
    coin = _coin(symbol="Y", best=None, label="")
    picks = rank_buy_picks([coin])
    assert picks[0]["bot_best_net_pct"] is None
