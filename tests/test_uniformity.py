from trendalgo.lts.adapter import OhlcvBar
from trendalgo.lts.uniformity import uniformity_score


def _bars(closes: list[float], *, body_pct: float = 0.01) -> list[OhlcvBar]:
    """Build OHLC bars with small bodies around each close for OHLCV composite."""
    out: list[OhlcvBar] = []
    for i, c in enumerate(closes):
        half = abs(c) * body_pct * 0.5 or 0.01
        out.append(
            OhlcvBar(
                i * 1000,
                open=c - half,
                high=c + half,
                low=c - half,
                close=c,
                volume=1.0,
            )
        )
    return out


def test_uniformity_insufficient_data() -> None:
    assert uniformity_score(_bars([1, 2, 3]), lookback=20) == 0.5


def test_uniformity_linear_uptrend_high() -> None:
    closes = [100 + i for i in range(25)]
    score = uniformity_score(_bars(closes), lookback=20)
    assert score >= 0.7


def test_uniformity_downtrend_low() -> None:
    # Bearish bodies + falling closes → trend gain ≤ 0 → composite stays low.
    closes = [100 - i for i in range(25)]
    bars = [
        OhlcvBar(i * 1000, open=c + 0.5, high=c + 0.6, low=c - 0.6, close=c, volume=1.0)
        for i, c in enumerate(closes)
    ]
    score = uniformity_score(bars, lookback=20)
    assert score <= 0.4
