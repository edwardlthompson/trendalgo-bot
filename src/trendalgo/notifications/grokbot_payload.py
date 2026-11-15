"""Structured JSON envelopes for the Grok Bot webhook (schema_version 1)."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from trendalgo.notifications.grokbot_config import SPARKLINE_MAX, bot_mode
from trendalgo.notifications.telegram_coin_fields import (
    coin_pair,
    exchange_volumes,
    gain_pct,
    listed_exchanges,
    uniformity_score,
    volume_24h,
)

SCHEMA_VERSION = "1"
EVENT_TYPES = (
    "scanner_alert",
    "qualified_enter",
    "qualified_leave",
    "trade_entry",
    "trade_exit",
    "test",
    "refit",
    "daily_summary",
)


def envelope(*, event_type: str, **fields: Any) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "event_type": event_type,
        "timestamp_utc": datetime.now(UTC)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z"),
        "bot_mode": bot_mode(),
        "pair": None,
        "exchange": None,
        "tier": None,
        "uniformity": None,
        "gain": None,
        "gains": None,
        "volume": None,
        "sparkline": None,
        "reason": None,
        "rationale": None,
        "strategy_id": None,
        "entry_price": None,
        "exit_price": None,
        "stake": None,
        "pnl": None,
        "exit_rule": None,
        "side": None,
    }
    for key, value in fields.items():
        if key in payload:
            payload[key] = value
    return payload


def sparkline_from(values: object) -> list[float] | None:
    if not isinstance(values, list) or not values:
        return None
    out: list[float] = []
    for item in values[-SPARKLINE_MAX:]:
        try:
            out.append(float(item))
        except (TypeError, ValueError):
            continue
    return out or None


def scanner_alert_payload(
    *,
    pair: str,
    tier: str,
    uniformity: float,
    gain: float,
    volume: float | None = None,
    sparkline: object = None,
    reason: str | None = None,
) -> dict[str, Any]:
    return envelope(
        event_type="scanner_alert",
        pair=pair,
        tier=tier,
        uniformity=uniformity,
        gain=gain,
        volume=volume,
        sparkline=sparkline_from(sparkline),
        reason=reason,
    )


def coin_payload(
    event_type: str, coin: dict[str, Any], *, reason: str | None = None
) -> dict[str, Any]:
    g7, g30 = gain_pct(coin, "7d"), gain_pct(coin, "30d")
    gains = {k: v for k, v in (("7d", g7), ("30d", g30)) if v is not None} or None
    exchanges = listed_exchanges(coin)
    vols = exchange_volumes(coin)
    exchange = exchanges[0] if exchanges else (next(iter(vols), None) if vols else None)
    spark = (
        coin.get("spark_closes_7d")
        or coin.get("chart_closes_1h")
        or coin.get("sparkline")
        or coin.get("closes")
    )
    return envelope(
        event_type=event_type,
        pair=coin_pair(coin),
        exchange=str(exchange) if exchange else None,
        uniformity=uniformity_score(coin),
        gain=g7 if g7 is not None else g30,
        gains=gains,
        volume=volume_24h(coin),
        sparkline=sparkline_from(spark),
        reason=reason,
        strategy_id=_strategy_id(coin),
    )


def trade_payload(
    *,
    pair: str,
    side: str,
    amount: float,
    price: float,
    realized_pnl_usd: float = 0.0,
    strategy_id: str | None = None,
    rationale: str | None = None,
    exit_rule: str | None = None,
    exchange: str | None = None,
    plan_version: int = 0,
) -> dict[str, Any]:
    kind = "trade_entry" if str(side).lower() in {"buy", "long"} else "trade_exit"
    is_exit = kind == "trade_exit"
    sid = strategy_id or (str(plan_version) if plan_version else None)
    return envelope(
        event_type=kind,
        pair=pair,
        exchange=exchange,
        side=str(side).lower(),
        stake=amount,
        entry_price=None if is_exit else price,
        exit_price=price if is_exit else None,
        pnl=realized_pnl_usd if is_exit else None,
        strategy_id=sid,
        rationale=rationale,
        reason=rationale if not is_exit else exit_rule or rationale,
        exit_rule=exit_rule if is_exit else None,
    )


def test_payload() -> dict[str, Any]:
    return envelope(event_type="test", reason="TrendAlgo Grok Bot webhook test")


def _strategy_id(coin: dict[str, Any]) -> str | None:
    for key in ("strategy_id", "best_strategy_id", "bot_strategy_id"):
        raw = coin.get(key)
        if raw:
            return str(raw)
    rows = coin.get("backtest_top_strategies") or coin.get("strategies") or []
    if isinstance(rows, list) and rows and isinstance(rows[0], dict):
        name = rows[0].get("id") or rows[0].get("name") or rows[0].get("indicator")
        return str(name) if name else None
    return None
