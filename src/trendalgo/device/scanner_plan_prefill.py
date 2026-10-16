"""Map scanner Results rows to Plan builder fields (LIVE_V1 only)."""

from __future__ import annotations

from typing import Any

from trendalgo.device.fields import (
    LIVE_V1_INDICATORS,
    TIMEFRAMES,
    TRAILING_STOP_MAX,
    TRAILING_STOP_MIN,
)

# Catalog / fleet strategy_id → live plan indicator label.
_CATALOG_TO_LIVE: dict[str, str] = {
    "RSI": "RSI",
    "MACD": "MACD",
    "EMA": "EMA Crossover",
    "SMA": "SMA Crossover",
    "BBANDS": "Bollinger %B",
    "HEIKIN ASHI": "Heikin Ashi",
    "HEIKINASHI": "Heikin Ashi",
    "HA": "Heikin Ashi",
}

_TF_ALIASES: dict[str, str] = {
    "1h": "1h",
    "4h": "4h",
    "60": "1h",
    "240": "4h",
    "1H": "1h",
    "4H": "4h",
}


def map_indicator_to_live(raw: str) -> str | None:
    """Return a LIVE_V1 label when the scanner indicator maps cleanly."""
    key = str(raw or "").strip()
    if not key:
        return None
    if key.endswith(" *"):
        key = key[:-2].strip()
    if key in LIVE_V1_INDICATORS:
        return key
    mapped = _CATALOG_TO_LIVE.get(key.upper())
    if mapped in LIVE_V1_INDICATORS:
        return mapped
    for label in LIVE_V1_INDICATORS:
        if label.casefold() == key.casefold():
            return label
    return None


def map_timeframe_to_plan(raw: str) -> str | None:
    text = str(raw or "").strip()
    if not text:
        return None
    mapped = _TF_ALIASES.get(text) or _TF_ALIASES.get(text.upper())
    if mapped in TIMEFRAMES:
        return mapped
    if text in TIMEFRAMES:
        return text
    return None


def integer_stop_pct(raw: object) -> str:
    """Integer trailing-stop percent string in [TRAILING_STOP_MIN, TRAILING_STOP_MAX]."""
    value: float | None = None
    if isinstance(raw, bool):
        value = None
    elif isinstance(raw, (int, float)):
        value = float(raw)
    elif isinstance(raw, str) and raw.strip():
        try:
            value = float(raw.strip())
        except ValueError:
            value = None
    if value is None or value <= 0:
        return f"{int(TRAILING_STOP_MIN)}"
    # Fleet stores fractions (0.05); Results sheet stores percent (5).
    pct = value * 100.0 if value <= 1.0 else value
    clamped = max(TRAILING_STOP_MIN, min(TRAILING_STOP_MAX, round(pct)))
    return f"{int(clamped)}"


def default_bot_name(
    *,
    exchange: str,
    pair: str,
    timeframe: str,
) -> str:
    """Auto name: exchange, pair, and timeframe."""
    ex = (exchange or "Kraken").strip() or "Kraken"
    pr = (pair or "").strip().upper() or "PAIR"
    tf = (timeframe or "1h").strip() or "1h"
    return f"{ex} {pr} {tf}"[:64]


def plan_prefill_from_scanner_row(
    row: dict[str, Any],
    *,
    pair: str,
    stake_usd: float = 100.0,
    exchange: str = "Kraken",
) -> tuple[dict[str, str] | None, str]:
    """Fields for Bots builder, or partial note when indicator is not live-mappable."""
    indicator_raw = str(row.get("indicator") or row.get("strategy_id") or "")
    live = map_indicator_to_live(indicator_raw)
    plan_tf = map_timeframe_to_plan(str(row.get("timeframe") or ""))
    tsl = row.get("trailing_stop_loss_pct")
    if tsl is None:
        tsl = row.get("trailing_stop_pct")
    stop = integer_stop_pct(tsl)
    tf = plan_tf or TIMEFRAMES[0]
    exch = str(row.get("exchange") or exchange or "Kraken")
    base = {
        "name": default_bot_name(exchange=exch, pair=pair, timeframe=tf),
        "pair": pair.strip().upper(),
        "timeframe": tf,
        "stake": f"{stake_usd:g}",
        "stop": stop,
        "strategy_id": indicator_raw,
    }
    if live is None:
        # Persist catalog id in the form; user can edit to a live label before Send.
        return {**base, "indicator": indicator_raw or ""}, (
            f"Indicator {indicator_raw!r} is not on the live host list yet "
            f"({', '.join(LIVE_V1_INDICATORS)}). Saved locally — edit before Send."
        )
    if plan_tf is None:
        tv = str(row.get("timeframe") or "")
        return {**base, "indicator": live}, (f"Timeframe {tv!r} is not on the device plan list.")
    return {**base, "indicator": live, "timeframe": plan_tf}, ""
