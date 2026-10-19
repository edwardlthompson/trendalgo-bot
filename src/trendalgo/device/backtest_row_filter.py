"""Column-filter predicates for Backtest strategy rows."""

from __future__ import annotations

from typing import Any

from trendalgo.device.indicator_strength import strength_from_row
from trendalgo.device.trade_counts import open_trades, wins_losses

_BH = "B&H"
_ORACLE = "Oracle max"
_KEEP = {_BH, _ORACLE}


def filter_rows(
    rows: list[dict[str, Any]],
    filters: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    if not filters:
        return list(rows)
    return [r for r in rows if row_matches(r, filters)]


def row_matches(row: dict[str, Any], filters: dict[str, Any]) -> bool:
    """True when row passes every active filter (B&H / Oracle max always kept)."""
    if str(row.get("indicator") or "").strip() in _KEEP:
        return True
    needle = str(filters.get("indicator_contains") or "").strip().lower()
    if needle and needle not in str(row.get("indicator") or "").lower():
        return False
    tf = str(filters.get("timeframe") or "").strip().lower()
    if tf and str(row.get("timeframe") or "").strip().lower() != tf:
        return False
    params_q = str(filters.get("params_contains") or "").strip().lower()
    if params_q and params_q not in _params_text(row).lower():
        return False
    checks = (
        ("net_pct", filters.get("min_net_pct"), True),
        ("fees_paid", filters.get("max_fees"), False),
        ("open_trades", filters.get("max_open"), False),
        ("wins", filters.get("min_wins"), True),
        ("losses", filters.get("max_losses"), False),
        ("win_pct", filters.get("min_win_pct"), True),
        ("tsl", filters.get("max_tsl_pct"), False),
        ("tsl_hits", filters.get("max_tsl_hits"), False),
        ("tsl_hit_pct", filters.get("max_tsl_hit_pct"), False),
        ("strength", filters.get("min_strength"), True),
    )
    for key, bound, is_min in checks:
        if not _bound_ok(
            row,
            key,
            bound,
            is_min=is_min,
            zero_ok=(key in {"tsl_hits", "open_trades"}),
        ):
            return False
    return True


def num_field(row: dict[str, Any], key: str) -> float:
    if key == "strength":
        value = strength_from_row(row)
        return value if value is not None else float("-inf")
    if key == "tsl":
        raw = row.get("trailing_stop_loss_pct")
        if raw is None:
            raw = row.get("trailing_stop_pct")
        return _num(raw, missing=float("-inf"))
    if key == "tsl_hit_pct":
        trades = _num(row.get("trades"), missing=0.0)
        hits = _num(row.get("tsl_hits"), missing=0.0)
        return hits / trades * 100.0 if trades > 0 else float("-inf")
    if key == "win_pct":
        raw = _num(row.get("win_pct"), missing=float("-inf"))
        if raw == float("-inf"):
            return raw
        return raw * 100.0 if 0.0 <= raw <= 1.0 else raw
    if key == "open_trades":
        raw = open_trades(row)
        return float(raw) if raw is not None else float("-inf")
    if key in {"wins", "losses"}:
        wins, losses = wins_losses(row)
        raw = wins if key == "wins" else losses
        return float(raw) if raw is not None else float("-inf")
    return _num(row.get(key), missing=float("-inf"))


def params_text(row: dict[str, Any]) -> str:
    return _params_text(row)


def _params_text(row: dict[str, Any]) -> str:
    params = row.get("params")
    if isinstance(params, dict):
        return " ".join(f"{k}={v}" for k, v in params.items())
    return str(params or "")


def _bound_ok(
    row: dict[str, Any],
    key: str,
    bound: object,
    *,
    is_min: bool,
    zero_ok: bool,
) -> bool:
    if bound is None or bound == "" or bound == "-":
        return True
    try:
        limit = float(bound)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return True
    if is_min:
        if limit <= 0:
            return True
        value = num_field(row, key)
        return value != float("-inf") and value >= limit
    if limit < 0 or (limit == 0 and not zero_ok):
        return True
    value = num_field(row, key)
    return value != float("-inf") and value <= limit


def _num(value: Any, *, missing: float) -> float:
    if value in (None, "-", ""):
        return missing
    try:
        return float(value)
    except (TypeError, ValueError):
        return missing
