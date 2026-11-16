"""CoinMarketCal Free-plan quota constants and refresh budget helpers."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

# Official Free V2 limits (https://coinmarketcal.com/developer/docs/rate-limits).
CMC_FREE_MONTHLY_QUOTA = 3000
CMC_FREE_AHEAD_DAYS = 7
CMC_PAID_AHEAD_DAYS = 30
CMC_REFRESH_RESERVE = 50
CMC_CACHE_MIN_AGE_S = 6 * 3600
CMC_MIN_INTERVAL_S = 1.0
CMC_FREE_RATE = 1  # req/sec
CMC_FREE_BURST = 5


@dataclass(frozen=True)
class UsageSnapshot:
    tier: str
    period_ym: str
    request_count: int
    monthly_quota: int | None
    remaining: int | None
    quota_reset_at: str


def usage_from_dict(raw: dict[str, Any]) -> UsageSnapshot:
    quota_raw = raw.get("monthlyQuota")
    rem_raw = raw.get("remaining")
    return UsageSnapshot(
        tier=str(raw.get("tier") or "free").lower(),
        period_ym=str(raw.get("periodYm") or ""),
        request_count=int(raw.get("requestCount") or 0),
        monthly_quota=int(quota_raw) if quota_raw is not None else None,
        remaining=int(rem_raw) if rem_raw is not None else None,
        quota_reset_at=str(raw.get("quotaResetAt") or ""),
    )


def effective_ahead_days(tier: str | None) -> int:
    t = (tier or "free").lower()
    if t in {"", "free"}:
        return CMC_FREE_AHEAD_DAYS
    return CMC_PAID_AHEAD_DAYS


def can_spend_refresh(
    usage: UsageSnapshot | None,
    *,
    cache_age_s: float | None,
    reserve: int = CMC_REFRESH_RESERVE,
    min_age_s: float = CMC_CACHE_MIN_AGE_S,
) -> tuple[bool, str]:
    """Whether a networked events refresh is allowed under Free budget rules."""
    if cache_age_s is not None and cache_age_s < min_age_s:
        return False, "cache_fresh"
    if usage is None:
        # No usage probe — allow a single events call (caller may skip usage).
        return True, "ok"
    if usage.remaining is not None and usage.remaining < reserve:
        return False, "quota_reserve"
    return True, "ok"


def cache_age_seconds(fetched_at_iso: str | None, *, now: datetime | None = None) -> float | None:
    if not fetched_at_iso:
        return None
    try:
        when = datetime.fromisoformat(fetched_at_iso.replace("Z", "+00:00"))
    except ValueError:
        return None
    if when.tzinfo is None:
        when = when.replace(tzinfo=UTC)
    stamp = now or datetime.now(tz=UTC)
    return max(0.0, (stamp - when).total_seconds())
