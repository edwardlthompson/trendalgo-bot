"""Search families → entry/exit CompositeRule seed pairs."""

from __future__ import annotations

from trendalgo.backtest.oracle_pattern_mine import CompositeRule, RuleConjunct
from trendalgo.backtest.secret_sauce_seeds import classic_pair_seeds

_FAT = 0.45  # weight >= this → full seed set
_SKIM_CAP = 4

# Cross-event level grids (edge semantics, not level-state). Dense toward Oracle.
_OSC_CROSS_PAIRS = (
    (30, 70),
    (25, 75),
    (35, 65),
    (30, 75),
    (25, 70),
    (35, 70),
    (30, 65),
    (23, 71),
    (23, 70),
    (20, 80),
    (28, 72),
    (32, 68),
    (25, 65),
)


def seeds_for_weights(
    strategy_id: str, weights: dict[str, float], *, volume_ok: bool
) -> list[tuple[CompositeRule, CompositeRule, str]]:
    """Return (entry, exit, family) pairs; fat families get full grids, others skim."""
    out: list[tuple[CompositeRule, CompositeRule, str]] = []
    for family, weight in weights.items():
        if family == "volume_impulse" and not volume_ok:
            continue
        pairs = _family_pairs(strategy_id, family)
        if weight < _FAT:
            pairs = pairs[:_SKIM_CAP]
        for er, xr in pairs:
            out.append((er, xr, family))
    # Always include classic RSI/stoch pairs as skim safety net.
    for er, xr in classic_pair_seeds(strategy_id)[:6]:
        out.append((er, xr, "classic"))
    return out


def _family_pairs(sid: str, family: str) -> list[tuple[CompositeRule, CompositeRule]]:
    if family == "osc_cross":
        return _osc_cross_pairs(sid)
    if family == "dip_uptrend":
        return [
            _pair(sid, (("rsi_14", "<=", el), ("above_sma50", ">=", 1.0)), (("rsi_14", ">=", xh),))
            for el, xh in ((40, 85), (45, 85), (45, 80), (40, 80), (35, 85), (30, 80))
        ]
    if family == "mean_reversion":
        # Level-state as skim companion; osc_cross family owns edge seeds.
        return [
            _pair(sid, (("rsi_14", "<=", el),), (("rsi_14", ">=", xh),))
            for el, xh in ((25, 70), (30, 70), (35, 75), (40, 75))
        ] + [
            _pair(sid, (("bb_pct_b", "<=", 0.2),), (("bb_pct_b", ">=", 0.8),)),
            _pair(sid, (("stoch_k", "<=", 20.0),), (("stoch_k", ">=", 80.0),)),
        ]
    if family == "momentum":
        return [
            _pair(
                sid,
                (("rsi_14", ">=", 55.0), ("above_sma20", ">=", 1.0)),
                (("macd_hist", "<=", 0.0),),
            ),
            _pair(
                sid,
                (("macd_hist", ">=", 0.0), ("above_sma50", ">=", 1.0)),
                (("rsi_14", "<=", 45.0),),
            ),
            _pair(sid, (("rsi_14", ">=", 60.0),), (("rsi_14", "<=", 40.0),)),
        ]
    if family == "squeeze_breakout":
        return [
            _pair(
                sid,
                (("bb_pct_b", "<=", 0.15), ("above_sma20", ">=", 1.0)),
                (("rsi_14", ">=", 70.0),),
            ),
            _pair(sid, (("bb_pct_b", "<=", 0.2),), (("bb_pct_b", ">=", 0.85),)),
            _pair(sid, (("atr_pct", "<=", 0.01),), (("rsi_14", ">=", 75.0),)),
        ]
    if family == "volume_impulse":
        return [
            _pair(
                sid, (("vol_ratio", ">=", 1.5), ("rsi_14", "<=", 40.0)), (("rsi_14", ">=", 70.0),)
            ),
            _pair(
                sid,
                (("vol_ratio", ">=", 2.0), ("above_sma50", ">=", 1.0)),
                (("rsi_14", ">=", 75.0),),
            ),
            _pair(sid, (("up_vol_impulse", ">=", 1.0),), (("peak_confirm", ">=", 1.0),)),
        ]
    return []


def _osc_cross_pairs(sid: str) -> list[tuple[CompositeRule, CompositeRule]]:
    out: list[tuple[CompositeRule, CompositeRule]] = []
    for el, xh in _OSC_CROSS_PAIRS:
        out.append(_pair(sid, ((f"rsi_xup_{el}", ">=", 1.0),), ((f"rsi_xdn_{xh}", ">=", 1.0),)))
        out.append(
            _pair(
                sid,
                ((f"rsi_xup_{el}", ">=", 1.0), ("above_sma50", ">=", 1.0)),
                ((f"rsi_xdn_{xh}", ">=", 1.0),),
            )
        )
        out.append(_pair(sid, ((f"rsx_xup_{el}", ">=", 1.0),), ((f"rsx_xdn_{xh}", ">=", 1.0),)))
        # Mixed oscillators — fee math often beats single-series clones toward Oracle.
        out.append(_pair(sid, ((f"rsi_xup_{el}", ">=", 1.0),), ((f"rsx_xdn_{xh}", ">=", 1.0),)))
        out.append(_pair(sid, ((f"rsx_xup_{el}", ">=", 1.0),), ((f"rsi_xdn_{xh}", ">=", 1.0),)))
    out.append(_pair(sid, (("stoch_xup_20", ">=", 1.0),), (("stoch_xdn_80", ">=", 1.0),)))
    out.append(_pair(sid, (("stoch_xup_25", ">=", 1.0),), (("stoch_xdn_75", ">=", 1.0),)))
    out.append(
        _pair(
            sid,
            (("stoch_xup_20", ">=", 1.0), ("above_sma20", ">=", 1.0)),
            (("stoch_xdn_80", ">=", 1.0),),
        )
    )
    return out


def _pair(
    sid: str,
    entry: tuple[tuple[str, str, float], ...],
    exit_: tuple[tuple[str, str, float], ...],
) -> tuple[CompositeRule, CompositeRule]:
    er = CompositeRule(
        strategy_id=sid,
        conjuncts=tuple(RuleConjunct(feature=f, op=o, value=float(v)) for f, o, v in entry),
        rationale="lab family entry",
    )
    xr = CompositeRule(
        strategy_id=sid,
        conjuncts=tuple(RuleConjunct(feature=f, op=o, value=float(v)) for f, o, v in exit_),
        rationale="lab family exit",
    )
    return er, xr
