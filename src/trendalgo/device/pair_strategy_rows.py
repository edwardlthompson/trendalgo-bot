"""Row catalog helpers for All-TA pair scan Results."""

from __future__ import annotations

from typing import Any

_BH = "B&H"


def ensure_full_catalog(
    rows: list[dict[str, Any]],
    strat_list: tuple[str, ...],
    *,
    symbol: str,
    stake_usd: float,
    skips: dict[str, str] | None = None,
) -> list[dict[str, Any]]:
    """After dedupe, fill missing indicators with honest skip_reason rows (+ keep B&H)."""
    present = {str(r.get("indicator") or "").strip().upper() for r in rows}
    skips = skips or {}
    filled = list(rows)
    for sid in strat_list:
        upper = str(sid).strip().upper()
        if not upper or upper in present or upper == _BH:
            continue
        reason = skips.get(upper) or skips.get(sid) or "no_trades"
        filled.append(
            skip_placeholder_row(upper, symbol=symbol, stake_usd=stake_usd, reason=reason)
        )
        present.add(upper)
    return collapse_bh_rows(filled)


def skip_placeholder_row(
    strategy_id: str,
    *,
    symbol: str,
    stake_usd: float,
    reason: str,
) -> dict[str, Any]:
    """Sheet row for an indicator that was tried but produced no tradable result."""
    stake = float(stake_usd) if stake_usd else 1.0
    return {
        "indicator": strategy_id.upper(),
        "timeframe": "—",
        "params": {},
        "trailing_stop_pct": None,
        "trailing_stop_loss_pct": None,
        "final_equity": stake,
        "net_pct": 0.0,
        "signal_net_pct": 0.0,
        "gross_profit": 0.0,
        "fees_paid": 0.0,
        "fee_taker_pct": None,
        "stake_usd": stake,
        "trades": 0,
        "win_pct": "-",
        "tsl_hits": 0,
        "symbol": symbol,
        "optimized": False,
        "skip_reason": reason,
    }


def remember_skip(best: dict[str, str], sid: str, reason: str) -> None:
    """Keep the most informative skip reason across TFs."""
    upper = str(sid).strip().upper()
    rank = {
        "compute_error": 0,
        "missing_backend": 1,
        "not_a_strategy": 2,
        "no_pattern": 3,
        "no_trades": 4,
        "insufficient_bars": 5,
    }
    prev = best.get(upper)
    if prev is None or rank.get(reason, 9) < rank.get(prev, 9):
        best[upper] = reason


def collapse_bh_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Keep a single B&H row — the best Net % — for the Backtest sheet."""
    best_bh: dict[str, Any] | None = None
    best_net = float("-inf")
    others: list[dict[str, Any]] = []
    for row in rows:
        if str(row.get("indicator") or "").strip() != _BH:
            others.append(row)
            continue
        try:
            net = float(row.get("net_pct"))  # type: ignore[arg-type]
        except (TypeError, ValueError):
            net = float("-inf")
        if net > best_net:
            best_bh, best_net = row, net
    if best_bh is not None:
        others.append(best_bh)
    return others


def dedupe_indicator_tf(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """One row per indicator — best Net % across TFs; prefer optimized on ties."""
    best: dict[str, dict[str, Any]] = {}
    bhs: list[dict[str, Any]] = []
    for row in rows:
        ind = str(row.get("indicator") or "").strip()
        if ind == _BH:
            bhs.append(row)
            continue
        prev = best.get(ind)
        if prev is None or _row_beats(row, prev):
            best[ind] = row
    return collapse_bh_rows(list(best.values()) + bhs)


def sort_rows_by_net(
    rows: list[dict[str, Any]], *, descending: bool = True
) -> list[dict[str, Any]]:
    """Sort by Net % (dir) → Win % desc → fewer TSL hits."""

    def key(row: dict[str, Any]) -> tuple[float, float, float]:
        net = _num(row.get("net_pct"), missing=float("-inf"))
        win = _num(row.get("win_pct"), missing=float("-inf"))
        hits = _num(row.get("tsl_hits"), missing=0.0)
        net_key = net if descending else -net
        return (net_key, win, -hits)

    return sorted(rows, key=key, reverse=True)


def _row_beats(candidate: dict[str, Any], incumbent: dict[str, Any]) -> bool:
    c_net = _num(candidate.get("net_pct"), missing=float("-inf"))
    i_net = _num(incumbent.get("net_pct"), missing=float("-inf"))
    if c_net != i_net:
        return c_net > i_net
    return bool(candidate.get("optimized")) and not bool(incumbent.get("optimized"))


def _num(value: Any, *, missing: float) -> float:
    if value in (None, "-", ""):
        return missing
    try:
        return float(value)
    except (TypeError, ValueError):
        return missing
