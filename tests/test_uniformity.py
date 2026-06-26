from trendalgo.lts.adapter import OhlcvBar
from trendalgo.lts.uniformity import uniformity_score


def _bars(closes: list[float]) -> list[OhlcvBar]:
    return [
        OhlcvBar(i * 1000, c, c, c, c, 1.0) for i, c in enumerate(closes)
    ]


def test_uniformity_insufficient_data() -> None:
    assert uniformity_score(_bars([1, 2, 3]), lookback=20) == 0.5


def test_uniformity_all_up() -> None:
    closes = list(range(25))
    assert uniformity_score(_bars(closes), lookback=20) == 1.0
