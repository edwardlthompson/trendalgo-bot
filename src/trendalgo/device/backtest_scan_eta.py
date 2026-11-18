"""Adaptive remaining-time estimates for the Backtest scan modal."""

from __future__ import annotations

import math
from dataclasses import dataclass

from trendalgo.device.backtest_notify import format_elapsed_s
from trendalgo.device.scan_time_history import ScanTimeHistory, estimate_coin_seconds

_LOG_SOFT_CAP = 200
_LIVE_WEIGHT = 0.7
_PRIOR_WEIGHT = 0.3


@dataclass(frozen=True)
class EtaSnapshot:
    """Glance metrics for one poll tick."""

    remaining_s: float | None
    pace_s: float | None
    prior_s: float
    live_s: float | None


def prior_seconds(
    hist: ScanTimeHistory,
    *,
    n_strategies: int,
    n_timeframes: int,
    had_subhour: bool,
) -> float:
    return estimate_coin_seconds(
        hist,
        n_strategies=n_strategies,
        n_timeframes=n_timeframes,
        had_subhour=had_subhour,
    )


def wall_coins_prior_s(*, per_coin_s: float, n_coins: int, coin_workers: int) -> float:
    """Parallel coin waves: ceil(n_coins / workers) × per-coin prior."""
    waves = max(1, math.ceil(max(1, int(n_coins)) / max(1, int(coin_workers))))
    return max(0.0, float(per_coin_s)) * waves


def remaining_from_units(
    *,
    unfinished_priors_s: float,
    workers: int,
    live_unit_s: float | None = None,
) -> EtaSnapshot:
    """Wall remaining from sum of unfinished unit priors ÷ workers."""
    wall = max(0.0, float(unfinished_priors_s)) / max(1, int(workers))
    pace_s = float(live_unit_s) if live_unit_s and live_unit_s > 0 else None
    return EtaSnapshot(
        remaining_s=wall if wall > 0 else None,
        pace_s=pace_s,
        prior_s=wall,
        live_s=None,
    )


def remaining_seconds(
    *,
    elapsed_s: float,
    done: int,
    total: int,
    prior_s: float,
    stamped_remaining_s: float | None = None,
) -> EtaSnapshot:
    """Blend historical prior with live pace once enough steps finished.

    When ``stamped_remaining_s`` is set (worker unit-sum ETA), prefer it.
    """
    if stamped_remaining_s is not None:
        stamp = max(0.0, float(stamped_remaining_s))
        pace_s = (float(elapsed_s) / done) if done >= 2 and elapsed_s > 0 else None
        return EtaSnapshot(
            remaining_s=stamp,
            pace_s=pace_s,
            prior_s=float(prior_s),
            live_s=pace_s * max(0, int(total) - int(done)) if pace_s is not None else None,
        )
    total_n = max(1, int(total))
    done_n = max(0, int(done))
    remaining_steps = max(0, total_n - done_n)
    prior_remain = max(0.0, float(prior_s) * (remaining_steps / total_n))
    live_s: float | None = None
    pace_s: float | None = None
    if done_n >= 2 and elapsed_s > 0:
        pace_s = float(elapsed_s) / done_n
        live_s = pace_s * remaining_steps
        blended = _LIVE_WEIGHT * live_s + _PRIOR_WEIGHT * prior_remain
        return EtaSnapshot(
            remaining_s=max(0.0, blended),
            pace_s=pace_s,
            prior_s=float(prior_s),
            live_s=live_s,
        )
    if done_n == 0:
        return EtaSnapshot(
            remaining_s=max(0.0, float(prior_s)) if prior_s > 0 else None,
            pace_s=None,
            prior_s=float(prior_s),
            live_s=None,
        )
    return EtaSnapshot(
        remaining_s=prior_remain if prior_s > 0 else None,
        pace_s=None,
        prior_s=float(prior_s),
        live_s=None,
    )


def format_remaining(remaining_s: float | None) -> str:
    if remaining_s is None:
        return "—"
    return format_elapsed_s(remaining_s)


def format_pace(pace_s: float | None) -> str:
    if pace_s is None or pace_s <= 0:
        return ""
    if pace_s < 10:
        return f"~{pace_s:.1f}s/step"
    return f"~{format_elapsed_s(pace_s)}/step"


def progress_pct(*, done: int, total: int, worker_ready: bool) -> int:
    """0–100; never 100% until the worker is ready."""
    total_n = max(1, int(total))
    done_n = max(0, int(done))
    pct = int(100 * done_n / total_n)
    if not worker_ready:
        pct = min(99, pct)
    return min(100, max(0, pct))


def append_log_line(lines: list[str], message: str, *, soft_cap: int = _LOG_SOFT_CAP) -> list[str]:
    """Append a distinct log line; drop consecutive duplicates; soft-cap length."""
    text = str(message or "").strip()
    if not text:
        return lines
    if lines and lines[-1] == text:
        return lines
    out = list(lines)
    out.append(text)
    if len(out) > soft_cap:
        out = out[-soft_cap:]
    return out
