"""LTS-style HTML Telegram bodies for scan enter/leave and trade fills."""

from __future__ import annotations

import html
from typing import Any

from trendalgo.notifications.telegram_coin_fields import (
    coin_name,
    coin_pair,
    coin_symbol,
    exchange_volumes,
    gain_pct,
    health_score,
    uniformity_score,
    volume_24h,
)
from trendalgo.notifications.telegram_keyboard import primary_market_url

_EX_EMOJI = {"coinbase": "🟦", "kraken": "🐙", "mexc": "🟪", "binance": "🟨"}
_CAP_MAX = 1024


def format_qualified_enter(coin: dict[str, Any]) -> str:
    """HTML caption for qualified enter (Telegram parse_mode=HTML)."""
    sym = _t(coin_symbol(coin))
    name = _t(coin_name(coin))
    url = primary_market_url(coin)
    if url:
        head = f'🟢 <a href="{_a(url)}">{sym} ({name})</a>\n\n'
    else:
        head = f"🟢 {sym} ({name})\n\n"
    lines = [head, "📊 Gains:\n"]
    g7, g30 = gain_pct(coin, "7d"), gain_pct(coin, "30d")
    lines.append(f"   7d: {_signed_pct(g7)}\n")
    lines.append(f"   30d: {_signed_pct(g30)}\n\n")
    uni = uniformity_score(coin)
    if uni is not None:
        lines.append(f"📈 Uniformity Score: {uni:.0f}/100\n")
    health = health_score(coin)
    if health is not None:
        label = coin.get("health_label")
        extra = f" ({_t(label)})" if label else ""
        lines.append(f"🩺 Health Score: {health:.0f}/100{extra}\n")
    rank = coin.get("current_rank")
    if isinstance(rank, int):
        lines.append(f"🏁 Rank: #{rank}\n")
    lines.append("\n")
    vol = volume_24h(coin)
    if vol is not None and vol > 0:
        lines.append(f"💵 Total 24h Volume: ${_num(vol)}\n\n")
    else:
        lines.append("💵 Total 24h Volume: —\n\n")
    vols = exchange_volumes(coin)
    # Only print venues that actually have volume (skip invented "No volume" rows).
    printed = False
    for key, raw in vols.items():
        if raw in (None, "", 0, "0", "N/A"):
            continue
        if not printed:
            lines.append("💰 Exchange Volumes:\n")
            printed = True
        emoji = _EX_EMOJI.get(str(key).lower(), "💱")
        label = str(key).title()
        if isinstance(raw, (int, float)):
            lines.append(f"{emoji} {label}: ${_num(float(raw))}\n")
        else:
            lines.append(f"{emoji} {label}: {_t(raw)}\n")
    # Strategy table lives on the chart image only (not the caption).
    return _cap("".join(lines))


def format_watchlist_leave(*, symbol: str, reason: str, coin: dict[str, Any] | None = None) -> str:
    """HTML leave body (LTS format_exit)."""
    body = coin or {"symbol": symbol}
    sym = _t(coin_symbol(body) if coin else symbol.upper())
    name = _t(coin_name(body) if coin else symbol.upper())
    url = primary_market_url(body) if coin else ""
    why = _t(reason or body.get("exit_reason") or "No longer met qualification criteria")
    parts = [f"🔴 {sym} ({name})\n"]
    if url:
        parts.append(f"🔗 {_t(url)}\n")
    parts.append("has left the qualified list\n")
    parts.append(f"Reason: {why}")
    life: list[str] = []
    for key, label in (
        ("lifecycle_pnl_pct", "P&L"),
        ("max_runup_pct", "Max↑"),
        ("max_drawdown_pct", "Max↓"),
    ):
        raw = body.get(key)
        if isinstance(raw, (int, float)):
            life.append(f"{label} {float(raw):+.2f}%")
    held = body.get("held_days")
    if isinstance(held, int):
        life.append(f"Held {held}d")
    if life:
        parts.append("\nLifecycle: " + " | ".join(life))
    return _cap("".join(parts))


def format_trade(
    *,
    pair: str,
    side: str,
    amount: float,
    price: float,
    fee_usd: float = 0.0,
    realized_pnl_usd: float = 0.0,
    plan_version: int = 0,
) -> str:
    return (
        f"Trade {side.upper()} {pair}\n"
        f"Amount: {amount:g} @ {price:g}\n"
        f"Fee: ${fee_usd:.4f}  PnL: ${realized_pnl_usd:.2f}\n"
        f"Plan v{plan_version}"
    )


def _t(value: object) -> str:
    return html.escape(str(value or ""), quote=False)


def _a(value: object) -> str:
    return html.escape(str(value or ""), quote=True)


def _cap(text: str) -> str:
    return text if len(text) <= _CAP_MAX else text[: _CAP_MAX - 1] + "…"


def _as_float(raw: object) -> float | None:
    try:
        return float(raw) if raw is not None and raw != "" else None  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None


def _signed_pct(raw: float | None) -> str:
    if raw is None:
        return "—"
    return f"{raw:+.1f}%"


def _num(value: float) -> str:
    if abs(value) >= 1_000_000:
        return f"{value / 1_000_000:.2f}M"
    if abs(value) >= 1_000:
        return f"{value:,.0f}"
    return f"{value:g}"


# Re-export for callers that only need pair display.
__all__ = [
    "coin_pair",
    "format_qualified_enter",
    "format_trade",
    "format_watchlist_leave",
]
