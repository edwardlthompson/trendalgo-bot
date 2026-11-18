"""Pure helpers for Backtest completion status, source badge, and notify copy."""

from __future__ import annotations

from trendalgo.device import strings as S


def format_elapsed_s(elapsed_s: float | int | None) -> str:
    """Human elapsed for status / toast (e.g. 45s, 2m 03s, 1h 02m)."""
    if elapsed_s is None:
        return "—"
    try:
        total = max(0, int(round(float(elapsed_s))))
    except (TypeError, ValueError):
        return "—"
    if total < 60:
        return f"{total}s"
    hours, rem = divmod(total, 3600)
    minutes, seconds = divmod(rem, 60)
    if hours:
        return f"{hours}h {minutes:02d}m"
    return f"{minutes}m {seconds:02d}s"


def format_cache_age(age_s: float | int | None) -> str:
    """Short cache age phrase (e.g. 12m ago, 2h ago)."""
    if age_s is None:
        return ""
    try:
        total = max(0, int(round(float(age_s))))
    except (TypeError, ValueError):
        return ""
    if total < 60:
        return f"{total}s ago"
    if total < 3600:
        return f"{total // 60}m ago"
    hours = total // 3600
    if hours < 48:
        return f"{hours}h ago"
    return f"{hours // 24}d ago"


def format_data_source(
    source: str | None,
    *,
    cache_age_s: float | int | None = None,
) -> str:
    """Honest provenance for Backtest / Scanner status."""
    raw = str(source or "").strip().lower()
    if not raw or raw in {"none", "unknown"}:
        return S.BACKTEST_SOURCE_PUBLIC
    if "synthetic" in raw:
        return S.BACKTEST_SOURCE_SYNTHETIC
    if "cache" in raw:
        age = format_cache_age(cache_age_s)
        if age:
            return S.BACKTEST_SOURCE_CACHED.format(age=age)
        return f"{S.BACKTEST_SOURCE_PUBLIC} · cached"
    if "keyed" in raw:
        return str(source).strip()
    return S.BACKTEST_SOURCE_PUBLIC


def done_status_line(
    *,
    elapsed_s: float | int | None = None,
    data_source: str | None = None,
    cache_age_s: float | int | None = None,
) -> str:
    """Status after a successful All-TA backtest."""
    parts = [S.BACKTEST_DONE]
    if elapsed_s is not None:
        parts.append(S.BACKTEST_ELAPSED.format(elapsed=format_elapsed_s(elapsed_s)))
    if data_source:
        badge = format_data_source(data_source, cache_age_s=cache_age_s)
        parts.append(S.BACKTEST_SOURCE_BADGE.format(source=badge))
    return " · ".join(parts)


def notify_title() -> str:
    return S.BACKTEST_DONE_TITLE


def notify_body(*, elapsed_s: float | int | None = None) -> str:
    return S.BACKTEST_DONE_BODY.format(elapsed=format_elapsed_s(elapsed_s))
