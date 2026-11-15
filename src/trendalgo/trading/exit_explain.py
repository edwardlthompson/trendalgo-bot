"""Label which native exit rule fired — recording only, never changes exit bool."""

from __future__ import annotations

from trendalgo.strategies.runtime.contract import Position, StrategyContext

FALLBACK = "native exit"


def describe_exit(strategy: object, ctx: StrategyContext, position: Position) -> str:
    """Call only after ``strategy.exit`` returned True. Does not re-decide the exit."""
    custom = getattr(strategy, "explain_exit", None)
    if callable(custom):
        try:
            labeled = custom(ctx, position)
        except Exception:
            labeled = None
        if labeled:
            return str(labeled)
    return _from_indicators(strategy, ctx) or FALLBACK


def _from_indicators(strategy: object, ctx: StrategyContext) -> str | None:
    df = getattr(ctx, "dataframe", None)
    if df is None or len(df) < 2:
        return None
    row = df.iloc[-1]
    prev = df.iloc[-2]
    sid = str(getattr(strategy, "strategy_id", "") or "")
    if "macd" in df.columns and "macd_signal" in df.columns:
        if prev["macd"] >= prev["macd_signal"] and row["macd"] < row["macd_signal"]:
            return "MACD cross down"
    if "rsi" in df.columns:
        try:
            rsi = float(row["rsi"])
        except (TypeError, ValueError):
            return None
        if rsi > 70:
            return "RSI threshold"
        if rsi > 65:
            return "RSI threshold"
        if sid == "grid-trading" and rsi > 58:
            return "RSI threshold"
    return None
