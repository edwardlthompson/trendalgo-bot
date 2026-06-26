"""Scanner uniformity — reuses LTS algorithm (O2)."""

from trendalgo.lts.adapter import OhlcvBar
from trendalgo.lts.uniformity import uniformity_score as lts_uniformity_score


def uniformity_score(bars: list[OhlcvBar], lookback: int = 20) -> float:
    return lts_uniformity_score(bars, lookback=lookback)
