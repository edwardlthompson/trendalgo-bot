"""Classic causal entry/exit seed pairs for Secret Sauce P&L search."""

from __future__ import annotations

from trendalgo.backtest.oracle_pattern_mine import CompositeRule, RuleConjunct


def classic_pair_seeds(strategy_id: str) -> list[tuple[CompositeRule, CompositeRule]]:
    """Paired RSI/stoch ± trend filter (dip-in-uptrend → extreme exit)."""
    pairs: list[tuple[CompositeRule, CompositeRule]] = []
    for el, xh in ((25, 70), (30, 70), (35, 75), (40, 75), (40, 70), (30, 65)):
        pairs.append(_rsi_pair(strategy_id, el, xh))
    for el, xh in ((40, 85), (45, 85), (45, 80), (40, 80), (35, 85)):
        pairs.append(_rsi_trend_pair(strategy_id, el, xh, sma="above_sma50"))
        pairs.append(_rsi_trend_pair(strategy_id, el, xh, sma="above_sma20"))
    for el, xh in ((20, 80), (25, 75), (30, 70)):
        er = CompositeRule(
            strategy_id=strategy_id,
            conjuncts=(RuleConjunct(feature="stoch_k", op="<=", value=float(el)),),
            rationale="classic stoch entry",
        )
        xr = CompositeRule(
            strategy_id=strategy_id,
            conjuncts=(RuleConjunct(feature="stoch_k", op=">=", value=float(xh)),),
            rationale="classic stoch exit",
        )
        pairs.append((er, xr))
    return pairs


def _rsi_pair(sid: str, el: int, xh: int) -> tuple[CompositeRule, CompositeRule]:
    er = CompositeRule(
        strategy_id=sid,
        conjuncts=(RuleConjunct(feature="rsi_14", op="<=", value=float(el)),),
        rationale="classic RSI entry",
    )
    xr = CompositeRule(
        strategy_id=sid,
        conjuncts=(RuleConjunct(feature="rsi_14", op=">=", value=float(xh)),),
        rationale="classic RSI exit",
    )
    return er, xr


def _rsi_trend_pair(sid: str, el: int, xh: int, *, sma: str) -> tuple[CompositeRule, CompositeRule]:
    er = CompositeRule(
        strategy_id=sid,
        conjuncts=(
            RuleConjunct(feature="rsi_14", op="<=", value=float(el)),
            RuleConjunct(feature=sma, op=">=", value=1.0),
        ),
        rationale=f"RSI dip + {sma}",
    )
    xr = CompositeRule(
        strategy_id=sid,
        conjuncts=(RuleConjunct(feature="rsi_14", op=">=", value=float(xh)),),
        rationale="RSI extreme exit",
    )
    return er, xr
