"""Assemble RegimeSnapshot + soft family budget weights."""

from __future__ import annotations

from collections import Counter
from dataclasses import asdict, dataclass
from typing import Any

import pandas as pd

from trendalgo.backtest.secret_sauce_features import has_real_volume
from trendalgo.backtest.secret_sauce_lab.regime_structural import (
    adx_di,
    choppiness_index,
    efficiency_ratio,
    sma,
)
from trendalgo.backtest.secret_sauce_lab.regime_volatility import (
    atr_percentile,
    bb_width_percentile,
    squeeze_flag,
)

FAMILIES = (
    "dip_uptrend",
    "mean_reversion",
    "osc_cross",
    "momentum",
    "squeeze_breakout",
    "volume_impulse",
)

_MAJORITY_BARS = 48


@dataclass(frozen=True)
class RegimeSnapshot:
    structural: str
    structural_confidence: float
    volatility: str
    direction: str
    squeeze: bool
    volume_ok: bool
    votes: dict[str, bool]
    family_weights: dict[str, float]
    narrative: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def detect_regime(df: pd.DataFrame) -> RegimeSnapshot:
    closes = df["close"].to_numpy(dtype=float)
    highs = df["high"].to_numpy(dtype=float) if "high" in df.columns else closes
    lows = df["low"].to_numpy(dtype=float) if "low" in df.columns else closes
    n = len(closes)
    i = n - 1
    adx, plus_di, minus_di = adx_di(highs, lows, closes)
    er = efficiency_ratio(closes)
    chop = choppiness_index(highs, lows, closes)
    atr_p = atr_percentile(highs, lows, closes)
    bb_p = bb_width_percentile(closes)
    sq = squeeze_flag(highs, lows, closes)
    sma20 = sma(closes, 20)
    sma50 = sma(closes, 50)
    sma100 = sma(closes, 100)

    start = max(0, n - _MAJORITY_BARS)
    structs: list[str] = []
    dirs: list[str] = []
    for j in range(start, n):
        st, _, _ = _structural_at(j, adx, er, chop, atr_p)
        structs.append(st)
        dirs.append(_direction_at(j, closes, plus_di, minus_di, sma20, sma50, sma100, st))

    structural = Counter(structs).most_common(1)[0][0] if structs else "transitional"
    direction = Counter(dirs).most_common(1)[0][0] if dirs else "flat"
    tip_st, tip_conf, tip_votes = _structural_at(i, adx, er, chop, atr_p)
    # Confidence from tip votes; label from majority window.
    conf = tip_conf if structural == tip_st else max(0.35, tip_conf * 0.8)

    vol_p = float(atr_p[i])
    if vol_p < 0.25:
        volatility = "low"
    elif vol_p > 0.75:
        volatility = "high"
    else:
        volatility = "normal"

    vote_adx = bool(adx[i] >= 20.0)
    vote_er = bool(er[i] >= 0.30)
    vote_chop = bool(chop[i] <= 55.0)
    slope20 = sma20[i] - sma20[max(0, i - 5)]
    ribbon_up = bool(sma20[i] >= sma50[i] >= sma100[i] and slope20 > 0)
    ribbon_dn = bool(sma20[i] <= sma50[i] <= sma100[i] and slope20 < 0)
    votes = {"adx": vote_adx, "er": vote_er, "chop": vote_chop, "ribbon": ribbon_up or ribbon_dn}

    volume_ok = has_real_volume(df)
    squeeze = bool(sq[i]) or bool(bb_p[i] < 0.20)
    weights = _family_weights(structural, volatility, direction, squeeze, volume_ok)
    narrative = (
        f"{structural} · vol={volatility} · dir={direction}"
        + (" · squeeze" if squeeze else "")
        + f" · votes ADX/ER/CHOP={tip_votes}/3 · maj{_MAJORITY_BARS}"
    )
    return RegimeSnapshot(
        structural=structural,
        structural_confidence=round(conf, 3),
        volatility=volatility,
        direction=direction,
        squeeze=squeeze,
        volume_ok=volume_ok,
        votes=votes,
        family_weights=weights,
        narrative=narrative,
    )


def _structural_at(
    i: int,
    adx: Any,
    er: Any,
    chop: Any,
    atr_p: Any,
) -> tuple[str, float, int]:
    vote_adx = bool(adx[i] >= 20.0)
    vote_er = bool(er[i] >= 0.30)
    vote_chop = bool(chop[i] <= 55.0)
    trend_votes = int(vote_adx) + int(vote_er) + int(vote_chop)
    vol_p = float(atr_p[i])
    if (chop[i] >= 61.8 and er[i] < 0.25) or (er[i] < 0.22 and vol_p > 0.70):
        return "choppy", min(1.0, max((chop[i] - 55.0) / 45.0, vol_p)), trend_votes
    if trend_votes >= 2:
        return "trending", trend_votes / 3.0, trend_votes
    if trend_votes == 0:
        return "ranging", 0.55, trend_votes
    return "transitional", 0.35, trend_votes


def _direction_at(
    i: int,
    closes: Any,
    plus_di: Any,
    minus_di: Any,
    sma20: Any,
    sma50: Any,
    sma100: Any,
    structural: str,
) -> str:
    slope20 = sma20[i] - sma20[max(0, i - 5)]
    ribbon_up = bool(sma20[i] >= sma50[i] >= sma100[i] and slope20 > 0)
    ribbon_dn = bool(sma20[i] <= sma50[i] <= sma100[i] and slope20 < 0)
    di_up = plus_di[i] >= minus_di[i]
    above50 = closes[i] >= sma50[i]
    if ribbon_up or (structural == "trending" and di_up and above50):
        return "up"
    if ribbon_dn or (structural == "trending" and not di_up):
        return "down"
    if above50 and slope20 > 0:
        return "up"
    if (not above50) and slope20 < 0:
        return "down"
    return "flat"


def _family_weights(
    structural: str,
    volatility: str,
    direction: str,
    squeeze: bool,
    volume_ok: bool,
) -> dict[str, float]:
    w = {k: 0.15 for k in FAMILIES}  # always skim
    if structural == "trending" and direction == "up":
        w["dip_uptrend"] = 1.0
        w["momentum"] = 0.85 if volatility == "high" else 0.7
        w["mean_reversion"] = 0.1 if volatility != "high" else 0.05
        w["osc_cross"] = 0.25
    elif structural == "trending" and direction == "down":
        # Edge crosses + MR; starve dip/squeeze heroes on down tapes.
        w["osc_cross"] = 1.0
        w["mean_reversion"] = 0.85
        w["dip_uptrend"] = 0.1
        w["momentum"] = 0.15
        w["squeeze_breakout"] = 0.1
    elif structural == "ranging" and volatility == "low":
        w["mean_reversion"] = 1.0
        w["osc_cross"] = 0.9
        w["momentum"] = 0.05
        w["dip_uptrend"] = 0.2
    elif structural == "choppy" or (structural == "ranging" and volatility == "high"):
        w = {k: 0.1 for k in FAMILIES}
        w["osc_cross"] = 0.35  # still try edges lightly
    else:
        w["mean_reversion"] = 0.5
        w["osc_cross"] = 0.55
        w["dip_uptrend"] = 0.4
        w["momentum"] = 0.35
    # Squeeze fat only when not a downtrend majority (avoid long squeeze on down tapes).
    if squeeze and direction != "down":
        w["squeeze_breakout"] = 1.0
    elif squeeze and direction == "down":
        w["squeeze_breakout"] = min(w["squeeze_breakout"], 0.15)
    if volume_ok and structural == "trending" and direction == "up":
        w["volume_impulse"] = max(w["volume_impulse"], 0.65)
    return {k: round(float(v), 3) for k, v in w.items()}
