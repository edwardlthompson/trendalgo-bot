"""Telegram chart helpers — closes extract + enter/exit alert PNGs."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from trendalgo.notifications.telegram_alert_image import build_enter_alert_png, build_exit_alert_png

__all__ = [
    "chart_png_bytes",
    "closes_from_coin",
    "enter_alert_png",
    "exit_alert_png",
]


def closes_from_coin(coin: dict[str, Any], *, window: str = "7d") -> list[float]:
    keys = (
        ("spark_closes_7d", "closes_7d", "chart_closes_1h", "closes")
        if window == "7d"
        else ("spark_closes_30d", "closes_30d", "closes")
    )
    for key in keys:
        raw = coin.get(key)
        if not isinstance(raw, list):
            continue
        out: list[float] = []
        for item in raw:
            try:
                out.append(float(item))
            except (TypeError, ValueError):
                continue
        if out:
            return out
    return []


def chart_png_bytes(
    closes: Sequence[float],
    *,
    title: str = "",
    hold_regions: Sequence[tuple[int, int]] | None = None,
) -> bytes | None:
    """Legacy close-line PNG; prefer enter_alert_png for alerts."""
    del hold_regions
    if len(closes) < 2:
        return None
    coin = {"symbol": title or "?", "spark_closes_7d": list(closes)}
    return build_enter_alert_png(coin)


def enter_alert_png(coin: dict[str, Any]) -> bytes | None:
    return build_enter_alert_png(coin)


def exit_alert_png(coin: dict[str, Any]) -> bytes | None:
    return build_exit_alert_png(coin)
