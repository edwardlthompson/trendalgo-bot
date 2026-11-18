"""AlgoSpecial free-tier budget: 1000/day, ≤50/min, 90m live-refresh floor."""

from __future__ import annotations

import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from trendalgo.device.profile import read_json, write_json

_FILE = "algospecial_budget.json"
DAILY_LIMIT = 1000
MAX_CALLS_PER_MIN = 50
# ~37 AlgoSpecial-served pairs → ⌊1000/37⌋ ≈ 27 refreshes/day → still ≥90m floor.
DEFAULT_PAIR_COUNT = 37


def min_live_refresh_minutes(n_pairs: int = DEFAULT_PAIR_COUNT) -> int:
    n = max(1, int(n_pairs))
    per_day = max(1, DAILY_LIMIT // n)
    return max(90, (24 * 60 + per_day - 1) // per_day)


def day_bucket(now: datetime | None = None) -> str:
    when = now or datetime.now(tz=UTC)
    if when.tzinfo is None:
        when = when.replace(tzinfo=UTC)
    return when.astimezone(UTC).strftime("%Y-%m-%d")


def load_budget(root: Path) -> dict[str, Any]:
    raw = read_json(root / _FILE)
    if not isinstance(raw, dict):
        return {"day": day_bucket(), "requests_used": 0, "last_live_fetch_at": None}
    day = str(raw.get("day") or day_bucket())
    used = int(raw.get("requests_used") or 0)
    if day != day_bucket():
        return {
            "day": day_bucket(),
            "requests_used": 0,
            "last_live_fetch_at": raw.get("last_live_fetch_at"),
        }
    return {
        "day": day,
        "requests_used": max(0, used),
        "last_live_fetch_at": raw.get("last_live_fetch_at"),
    }


def save_budget(root: Path, payload: dict[str, Any]) -> None:
    write_json(root / _FILE, payload)


def can_fetch(root: Path, n: int, *, n_pairs: int = DEFAULT_PAIR_COUNT) -> tuple[bool, str]:
    """Return (ok, reason). Cool-down and daily cap both block live pulls."""
    need = max(0, int(n))
    if need <= 0:
        return True, "noop"
    state = load_budget(root)
    used = int(state.get("requests_used") or 0)
    if used + need > DAILY_LIMIT:
        return False, f"daily_cap ({used}+{need}>{DAILY_LIMIT})"
    last = state.get("last_live_fetch_at")
    floor_m = min_live_refresh_minutes(n_pairs)
    if isinstance(last, str) and last:
        try:
            prev = datetime.fromisoformat(last)
            if prev.tzinfo is None:
                prev = prev.replace(tzinfo=UTC)
            elapsed_m = (datetime.now(tz=UTC) - prev.astimezone(UTC)).total_seconds() / 60.0
            if elapsed_m < floor_m:
                left = int(floor_m - elapsed_m) + 1
                return False, f"cooldown_{left}m"
        except ValueError:
            pass
    return True, "ok"


def record_fetch(root: Path, n: int, *, mark_live: bool = True) -> dict[str, Any]:
    state = load_budget(root)
    state["day"] = day_bucket()
    state["requests_used"] = int(state.get("requests_used") or 0) + max(0, int(n))
    if mark_live:
        state["last_live_fetch_at"] = datetime.now(tz=UTC).isoformat()
    save_budget(root, state)
    return state


class PaceGate:
    """Sleep so successive HTTP calls stay under MAX_CALLS_PER_MIN."""

    def __init__(self, *, max_per_min: float = MAX_CALLS_PER_MIN) -> None:
        self._min_interval = 60.0 / max(1.0, float(max_per_min))
        self._last = 0.0

    def wait(self) -> None:
        if self._last <= 0:
            self._last = time.monotonic()
            return
        elapsed = time.monotonic() - self._last
        if elapsed < self._min_interval:
            time.sleep(self._min_interval - elapsed)
        self._last = time.monotonic()
