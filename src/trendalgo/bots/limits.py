"""Bot count and sub-minute timeframe guardrails."""

from __future__ import annotations

from typing import Any

# Total bots — high cap; SQLite + UI remain practical limits.
MAX_BOTS_TOTAL = 500

# Concurrent enabled bots (TA + OHLCV work scales with enabled count).
MAX_ENABLED_BOTS_PAPER = 50
MAX_ENABLED_BOTS_LIVE = 20

# Sub-minute intervals (1S–30S) are CPU/network intensive.
SUB_MINUTE_INTERVALS: frozenset[str] = frozenset({"1S", "5S", "15S", "30S"})
MAX_SUB_MINUTE_ENABLED_PAPER = 3
MAX_SUB_MINUTE_ENABLED_LIVE = 1
MAX_1S_ENABLED = 1

# OHLCV chart window caps (avoid multi-million bar fetches at 1S).
CHART_LOOKBACK_SECONDS: dict[str, int] = {
    "1S": 3_600,  # 1 hour → 3,600 bars
    "5S": 14_400,  # 4 hours
    "15S": 43_200,  # 12 hours
    "30S": 86_400,  # 24 hours
}
DEFAULT_CHART_LOOKBACK_SECONDS = 30 * 86_400  # 30 days


def interval_seconds(tv_interval: str) -> int:
    from trendalgo.constants.timeframes import normalize_tv_interval

    key = normalize_tv_interval(tv_interval)
    if key in SUB_MINUTE_INTERVALS:
        return int(key[:-1])
    if key.isdigit():
        return int(key) * 60
    if key == "1D":
        return 86_400
    if key == "1W":
        return 7 * 86_400
    return 3_600


def is_sub_minute(tv_interval: str) -> bool:
    from trendalgo.constants.timeframes import normalize_tv_interval

    return normalize_tv_interval(tv_interval) in SUB_MINUTE_INTERVALS


def chart_lookback_seconds(tv_interval: str) -> int:
    from trendalgo.constants.timeframes import normalize_tv_interval

    return CHART_LOOKBACK_SECONDS.get(normalize_tv_interval(tv_interval), DEFAULT_CHART_LOOKBACK_SECONDS)


def max_ohlcv_bars(tv_interval: str) -> int:
    """Max bars to retain for TA at this interval."""
    secs = interval_seconds(tv_interval)
    window = chart_lookback_seconds(tv_interval)
    return max(200, window // max(secs, 1))


def _count_sub_minute_enabled(bots: list[dict[str, Any]], *, include_1s_only: bool = False) -> int:
    n = 0
    for bot in bots:
        if not bot.get("enabled"):
            continue
        tf = str(bot.get("timeframe") or "60")
        if include_1s_only:
            from trendalgo.constants.timeframes import normalize_tv_interval

            if normalize_tv_interval(tf) == "1S":
                n += 1
        elif is_sub_minute(tf):
            n += 1
    return n


def _enabled_count(bots: list[dict[str, Any]]) -> int:
    return sum(1 for b in bots if b.get("enabled"))


def validate_bot_capacity(
    bots: list[dict[str, Any]],
    *,
    paper: bool,
    adding: bool = False,
    enabling: bool = False,
    timeframe: str = "60",
    exclude_bot_id: int | None = None,
) -> None:
    """Raise ValueError when a bot operation would exceed guardrails."""
    scoped = [b for b in bots if exclude_bot_id is None or int(b["id"]) != exclude_bot_id]

    if adding and len(scoped) >= MAX_BOTS_TOTAL:
        raise ValueError(
            f"Bot limit reached ({MAX_BOTS_TOTAL} max). "
            "Each bot stores settings and chart history - too many slows the dashboard. "
            "Delete bots you no longer use."
        )

    max_enabled = MAX_ENABLED_BOTS_PAPER if paper else MAX_ENABLED_BOTS_LIVE
    enabled = _enabled_count(scoped)
    if enabling and enabled >= max_enabled:
        raise ValueError(
            f"Running bot limit reached ({max_enabled} max in {'paper' if paper else 'live'} mode). "
            "Each running bot fetches OHLCV and recomputes TA every bar — too many causes lag and missed signals. "
            "Pause another bot first."
        )

    if not is_sub_minute(timeframe) or not enabling:
        return

    from trendalgo.constants.timeframes import normalize_tv_interval

    tf = normalize_tv_interval(timeframe)
    sub_max = MAX_SUB_MINUTE_ENABLED_PAPER if paper else MAX_SUB_MINUTE_ENABLED_LIVE
    sub_count = _count_sub_minute_enabled(scoped)
    if sub_count >= sub_max:
        raise ValueError(
            f"Sub-minute bot limit reached ({sub_max} max at 1S–30S). "
            "Sub-minute bars trigger TA on thousands of OHLCV rows every few seconds — "
            "capping these keeps charts responsive. Use 1-minute or higher for more bots."
        )
    if tf == "1S":
        one_s = _count_sub_minute_enabled(scoped, include_1s_only=True)
        if one_s >= MAX_1S_ENABLED:
            raise ValueError(
                "Only one bot may run at the 1-second timeframe. "
                "At 1S the app recomputes indicators on ~3,600 bars every second — "
                "a second 1S bot would double CPU load and stall the UI. Use 5S or higher."
            )


def limits_payload(*, paper: bool) -> dict[str, Any]:
    return {
        "max_bots_total": MAX_BOTS_TOTAL,
        "max_enabled_bots": MAX_ENABLED_BOTS_PAPER if paper else MAX_ENABLED_BOTS_LIVE,
        "max_sub_minute_enabled": MAX_SUB_MINUTE_ENABLED_PAPER if paper else MAX_SUB_MINUTE_ENABLED_LIVE,
        "max_1s_enabled": MAX_1S_ENABLED,
        "sub_minute_intervals": sorted(SUB_MINUTE_INTERVALS),
        "chart_lookback_seconds": CHART_LOOKBACK_SECONDS,
        "paper": paper,
        "ohlcv_cache": {
            "bot_scoped": True,
            "dedupe_shared_pair_timeframe": True,
            "limits_adjustment": "none",
            "reason": (
                "Bot-scoped SQLite OHLCV cache avoids repeated Kraken downloads for pairs your bots "
                "use and lets multiple bots on the same pair share one candle series. Indicator "
                "recomputation still runs per bot each bar (CPU-bound), so running-bot caps are unchanged."
            ),
        },
        "ta_cache": {
            "shared_fingerprint": True,
            "incremental_tail": True,
            "limits_adjustment": "none",
            "reason": (
                "Bots with the same pair, timeframe, strategy, and TA parameters share one in-memory "
                "signal cache. When a new bar appends, only the tail window is recomputed. Running-bot "
                "caps stay unchanged until benchmark proves ≥40% p95 TA savings."
            ),
        },
    }
