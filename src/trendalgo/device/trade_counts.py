"""Derive win / loss / open trade counts from a Backtest / LTS row."""

from __future__ import annotations

from typing import Any


def wins_losses(row: dict[str, Any]) -> tuple[int | None, int | None]:
    """Return (wins, losses) among closed trades, or (None, None) when unknown."""
    trades = _as_int(row.get("trades"))
    if trades is None or trades < 0:
        return None, None
    open_n = open_trades(row) or 0
    open_n = max(0, min(open_n, trades))
    closed = trades - open_n
    wins = _wins(row, closed)
    return wins, max(0, closed - wins)


def open_trades(row: dict[str, Any]) -> int | None:
    """Trades still open at the last bar (force-settled for P&L, not a real exit)."""
    raw = row.get("open_trades")
    if raw is not None and raw not in ("-", ""):
        try:
            return max(0, int(raw))
        except (TypeError, ValueError):
            pass
    trades = _as_int(row.get("trades"))
    if trades is None:
        return None
    return 0


def _wins(row: dict[str, Any], closed: int) -> int:
    raw = row.get("wins")
    if raw is not None and raw not in ("-", ""):
        try:
            return max(0, min(int(raw), closed))
        except (TypeError, ValueError):
            pass
    win = row.get("win_pct")
    try:
        rate = float(win)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return 0
    if closed <= 0:
        return 0
    if 0.0 <= rate <= 1.0:
        return int(round(rate * closed))
    return int(round((rate / 100.0) * closed))


def _as_int(value: Any) -> int | None:
    if value in (None, "-"):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None
