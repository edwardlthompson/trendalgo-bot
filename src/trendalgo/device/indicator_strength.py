"""Indicator Strength: Wilson win-rate lower bound × TSL-exit quality.

Trading literature has no single “indicator strength” standard. Closest cousins:
Van Tharp SQN (needs R-multiples), profit factor, and Wilson score intervals used
for ranking binomial rates with small samples (e.g. upvote ranking).

We use Wilson’s lower bound so 2/2 wins score far below 20/20, then multiply by
(1 − TSL-hit share)^1.5 so strategies that only survive via trailing stops rank low.
"""

from __future__ import annotations

import math
from typing import Any

_BH = "B&H"
_Z = 1.96  # ~95% Wilson interval


def wilson_lower_bound(wins: int, n: int, *, z: float = _Z) -> float:
    """Lower bound of Wilson score interval for wins/n in [0, 1]."""
    if n <= 0:
        return 0.0
    wins = max(0, min(int(wins), int(n)))
    p = wins / n
    z2 = z * z
    denom = 1.0 + z2 / n
    centre = p + z2 / (2.0 * n)
    margin = z * math.sqrt((p * (1.0 - p) + z2 / (4.0 * n)) / n)
    return max(0.0, min(1.0, (centre - margin) / denom))


def indicator_strength(
    *,
    trades: int,
    wins: int,
    tsl_hits: int,
) -> float | None:
    """Score 0–100, or None when there are no closed trades."""
    n = int(trades)
    if n <= 0:
        return None
    hits = max(0, min(int(tsl_hits), n))
    win_n = max(0, min(int(wins), n))
    tsl_share = hits / n
    exit_quality = (1.0 - tsl_share) ** 1.5
    score = 100.0 * wilson_lower_bound(win_n, n) * exit_quality
    return float(f"{score:.1f}")


def strength_from_row(row: dict[str, Any]) -> float | None:
    """Compute strength from a Backtest / LTS strategy row (closed trades only)."""
    if str(row.get("indicator") or "").strip() == _BH:
        return None
    trades = _as_int(row.get("trades"))
    if trades is None or trades <= 0:
        return None
    open_n = _as_int(row.get("open_trades")) or 0
    closed = max(0, trades - max(0, min(open_n, trades)))
    if closed <= 0:
        return None
    hits = _as_int(row.get("tsl_hits")) or 0
    wins = _wins(row, closed)
    return indicator_strength(trades=closed, wins=wins, tsl_hits=hits)


def _wins(row: dict[str, Any], trades: int) -> int:
    raw = row.get("wins")
    if raw is not None and raw not in ("-", ""):
        try:
            return max(0, min(int(raw), trades))
        except (TypeError, ValueError):
            pass
    win = row.get("win_pct")
    try:
        rate = float(win)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return 0
    # 0–1 fraction or 0–100 percent
    if 0.0 <= rate <= 1.0:
        return int(round(rate * trades))
    return int(round((rate / 100.0) * trades))


def _as_int(value: Any) -> int | None:
    if value in (None, "-", ""):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None
