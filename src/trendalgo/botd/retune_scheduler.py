"""Daily UTC retune scheduler (LIVE-01)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any

from trendalgo.backtest.secret_sauce_lab.search_folds import bar_folds

MIN_WINDOW = 500
MAX_WINDOW = 1000
DEFAULT_PURGE = 4


def clamp_rolling_window(
    bar_count: int, *, min_bars: int = MIN_WINDOW, max_bars: int = MAX_WINDOW
) -> int:
    """Fixed rolling window; never the full series beyond max_bars."""
    n = max(0, int(bar_count))
    if n <= 0:
        return min_bars
    return max(min_bars, min(n, max_bars))


def due_for_retune(
    now_utc: datetime,
    last_retune_utc: datetime | None,
    *,
    strategy_tf_hours: float,
    scheduled_hour_utc: int = 6,
) -> bool:
    """Daily at fixed UTC hour; never faster than 1/24 of strategy timeframe."""
    now = now_utc.astimezone(UTC)
    if now.hour != int(scheduled_hour_utc):
        return False
    # Daily floor (24h) and TF floor (tf_hours / 24).
    min_gap = timedelta(hours=max(24.0, float(strategy_tf_hours) / 24.0))
    if last_retune_utc is None:
        return True
    last = last_retune_utc.astimezone(UTC)
    return (now - last) >= min_gap


def pick_verdict(*, incumbent_net: float, candidate_net: float) -> str:
    """Incumbent is default; no_change wins ties."""
    if candidate_net > incumbent_net:
        return "propose"
    return "no_change"


@dataclass(frozen=True)
class RetuneCycle:
    window_bars: int
    train_indexes: list[int]
    holdout_indexes: list[int]
    verdict: str
    incumbent_params: dict[str, Any]
    candidate_params: dict[str, Any]
    journal: dict[str, Any] = field(default_factory=dict)


def run_retune_cycle(
    *,
    bar_count: int,
    incumbent_params: dict[str, Any],
    candidate_params: dict[str, Any],
    incumbent_net: float,
    candidate_net: float,
    purge_bars: int = DEFAULT_PURGE,
    now_utc: datetime | None = None,
) -> RetuneCycle:
    """One retune cycle: rolling window, purged folds, journal inputs/candidates/verdict."""
    window = clamp_rolling_window(bar_count)
    train, hold = bar_folds(window, holdout_frac=0.35, purge_bars=purge_bars)
    verdict = pick_verdict(incumbent_net=incumbent_net, candidate_net=candidate_net)
    ts = (now_utc or datetime.now(UTC)).astimezone(UTC).replace(microsecond=0).isoformat()
    journal = {
        "ts": ts,
        "inputs": {
            "bar_count": bar_count,
            "window_bars": window,
            "purge_bars": purge_bars,
            "incumbent_net": incumbent_net,
            "candidate_net": candidate_net,
        },
        "candidates": [
            {"role": "incumbent", "params": dict(incumbent_params), "net": incumbent_net},
            {"role": "candidate", "params": dict(candidate_params), "net": candidate_net},
        ],
        "verdict": verdict,
    }
    return RetuneCycle(
        window_bars=window,
        train_indexes=train,
        holdout_indexes=hold,
        verdict=verdict,
        incumbent_params=dict(incumbent_params),
        candidate_params=dict(candidate_params),
        journal=journal,
    )
