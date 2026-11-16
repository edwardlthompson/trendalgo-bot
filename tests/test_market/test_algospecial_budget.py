"""FX-AS2: AlgoSpecial day budget, cooldown, pace floor."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

from trendalgo.market.algospecial_budget import (
    DAILY_LIMIT,
    can_fetch,
    load_budget,
    min_live_refresh_minutes,
    record_fetch,
    save_budget,
)


def test_min_live_refresh_floor_90() -> None:
    assert min_live_refresh_minutes(59) == 90
    assert min_live_refresh_minutes(1) >= 90


def test_can_fetch_daily_cap(tmp_path: Path) -> None:
    save_budget(
        tmp_path,
        {"day": datetime.now(tz=UTC).strftime("%Y-%m-%d"), "requests_used": DAILY_LIMIT - 1},
    )
    ok, reason = can_fetch(tmp_path, 2, n_pairs=59)
    assert ok is False
    assert "daily_cap" in reason


def test_can_fetch_cooldown(tmp_path: Path) -> None:
    recent = (datetime.now(tz=UTC) - timedelta(minutes=10)).isoformat()
    save_budget(
        tmp_path,
        {
            "day": datetime.now(tz=UTC).strftime("%Y-%m-%d"),
            "requests_used": 0,
            "last_live_fetch_at": recent,
        },
    )
    ok, reason = can_fetch(tmp_path, 1, n_pairs=59)
    assert ok is False
    assert reason.startswith("cooldown_")


def test_record_fetch_increments(tmp_path: Path) -> None:
    state = record_fetch(tmp_path, 3, mark_live=True)
    assert state["requests_used"] == 3
    assert isinstance(state["last_live_fetch_at"], str)
    loaded = load_budget(tmp_path)
    assert loaded["requests_used"] == 3
