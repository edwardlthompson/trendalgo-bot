"""Peer-class seed inspiration — not RSI-only."""

from __future__ import annotations

from typing import Any

from trendalgo.backtest.oracle_pattern_mine import CompositeRule, RuleConjunct
from trendalgo.backtest.secret_sauce_lab.catalog_reseed import inspire_cross_seeds, is_rsx_like_hint
from trendalgo.backtest.secret_sauce_lab.families import seeds_for_weights

_SID = "GEN_SECRET_1"


def inspire_seeds_for_hints(
    strategy_id: str,
    hints: list[dict[str, Any]],
) -> list[tuple[CompositeRule, CompositeRule, str]]:
    """Route by peer kind; include RSI/stoch mutants for osc peers."""
    out: list[tuple[CompositeRule, CompositeRule, str]] = []
    seen: set[tuple[str, ...]] = set()
    for hint in hints[:3]:
        kind = str(hint.get("kind") or "")
        for er, xr, fam in _seeds_for_kind(strategy_id, kind, hint):
            key = _sig(er, xr)
            if key in seen:
                continue
            seen.add(key)
            out.append((er, xr, fam))
    # Always skim osc mutants from RSX-like peers in the hint set.
    osc_hints = [h for h in hints if is_rsx_like_hint(h)]
    if osc_hints:
        for er, xr, fam in inspire_cross_seeds(strategy_id, osc_hints[:2]):
            key = _sig(er, xr)
            if key in seen:
                continue
            seen.add(key)
            out.append((er, xr, fam))
    return out


def should_run_rsx_neighborhood(hints: list[dict[str, Any]]) -> bool:
    return any(is_rsx_like_hint(h) for h in hints[:3])


def _seeds_for_kind(
    sid: str, kind: str, hint: dict[str, Any]
) -> list[tuple[CompositeRule, CompositeRule, str]]:
    if kind in {"macd_cross", "zero_cross"}:
        return [
            (
                _rule(sid, (("macd_hist", ">=", 0.0), ("above_sma20", ">=", 1.0))),
                _rule(sid, (("macd_hist", "<=", 0.0),)),
                "peer_macd",
            ),
            (
                _rule(sid, (("macd_hist", ">=", 0.0), ("above_sma50", ">=", 1.0))),
                _rule(sid, (("rsi_14", "<=", 45.0),)),
                "peer_macd",
            ),
        ]
    if kind in {"ma_cross", "price_cross"}:
        return [
            (
                _rule(sid, (("above_sma50", ">=", 1.0), ("trough_confirm", ">=", 1.0))),
                _rule(sid, (("peak_confirm", ">=", 1.0),)),
                "peer_ma",
            ),
            (
                _rule(sid, (("above_sma20", ">=", 1.0), ("ret_1", ">=", 0.0))),
                _rule(sid, (("rsi_14", ">=", 70.0),)),
                "peer_ma",
            ),
        ]
    if kind == "cdl_pattern":
        return [
            (
                _rule(sid, (("trough_confirm", ">=", 1.0), ("vol_z", ">=", 0.5))),
                _rule(sid, (("peak_confirm", ">=", 1.0),)),
                "peer_cdl",
            ),
            (
                _rule(sid, (("trough_confirm", ">=", 1.0), ("up_vol_impulse", ">=", 1.0))),
                _rule(sid, (("rsi_14", ">=", 70.0),)),
                "peer_cdl",
            ),
        ]
    if kind == "bounded_reversal" or is_rsx_like_hint(hint):
        return []  # RSI/stoch via inspire_cross_seeds
    # Unknown: fat all families skim.
    weights = {
        "dip_uptrend": 1.0,
        "mean_reversion": 1.0,
        "osc_cross": 1.0,
        "momentum": 1.0,
        "squeeze_breakout": 0.5,
        "volume_impulse": 0.5,
    }
    return [(er, xr, "peer_fat") for er, xr, _f in seeds_for_weights(sid, weights, volume_ok=True)]


def _rule(sid: str, conj: tuple[tuple[str, str, float], ...]) -> CompositeRule:
    return CompositeRule(
        strategy_id=sid,
        conjuncts=tuple(RuleConjunct(feature=f, op=o, value=float(v)) for f, o, v in conj),
        rationale="peer-class inspire",
    )


def _sig(er: CompositeRule, xr: CompositeRule) -> tuple[str, ...]:
    return tuple(c.feature for c in er.conjuncts) + ("|",) + tuple(c.feature for c in xr.conjuncts)
