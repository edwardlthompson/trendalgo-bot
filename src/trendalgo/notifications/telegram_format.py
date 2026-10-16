"""Plain-text Telegram bodies for scan enter/leave and trade fills."""

from __future__ import annotations

from typing import Any


def format_qualified_enter(coin: dict[str, Any]) -> str:
    symbol = str(coin.get("symbol") or coin.get("pair") or "?").upper()
    pair = str(coin.get("pair") or symbol)
    gain7 = _pct(coin.get("gain_7d"))
    gain30 = _pct(coin.get("gain_30d"))
    health = coin.get("health")
    unit = coin.get("uniformity")
    vol = coin.get("volume_24h") or coin.get("vol24")
    exchanges = coin.get("listed_on") or []
    ex_text = (
        ", ".join(str(x) for x in exchanges) if isinstance(exchanges, list) else str(exchanges)
    )
    lines = [
        f"Qualified: {symbol}",
        f"Pair: {pair}",
        f"7d: {gain7}  30d: {gain30}",
        f"Health: {_num(health)}  Uniformity: {_num(unit)}",
        f"24h vol: {_num(vol)}",
        f"Exchanges: {ex_text or '—'}",
    ]
    table = _strategy_table(coin)
    if table:
        lines.append("")
        lines.append(table)
    return "\n".join(lines)


def format_watchlist_leave(*, symbol: str, reason: str) -> str:
    return f"Left qualified: {symbol}\n{reason}"


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


def _strategy_table(coin: dict[str, Any]) -> str:
    rows = coin.get("strategies") or coin.get("top_strategies") or []
    if not isinstance(rows, list) or not rows:
        best = coin.get("best_bt") or coin.get("best_strategy")
        if best:
            return f"Best BT: {best}"
        return ""
    lines = ["Strategy | PnL% | vs B&H"]
    for row in rows[:8]:
        if not isinstance(row, dict):
            continue
        name = str(row.get("name") or row.get("id") or "?")
        pnl = _pct(row.get("pnl_pct") or row.get("return_pct"))
        vs = _pct(row.get("vs_bh") or row.get("beat_bh_pct"))
        lines.append(f"{name} | {pnl} | {vs}")
    return "\n".join(lines)


def _pct(raw: object) -> str:
    if raw is None or raw == "":
        return "—"
    if isinstance(raw, bool) or not isinstance(raw, int | float | str):
        return str(raw)
    try:
        return f"{float(raw):.1f}%"
    except (TypeError, ValueError):
        return str(raw)


def _num(raw: object) -> str:
    if raw is None or raw == "":
        return "—"
    if isinstance(raw, bool) or not isinstance(raw, int | float | str):
        return str(raw)
    try:
        value = float(raw)
    except (TypeError, ValueError):
        return str(raw)
    if abs(value) >= 1_000_000:
        return f"{value / 1_000_000:.2f}M"
    if abs(value) >= 1_000:
        return f"{value / 1_000:.1f}k"
    return f"{value:g}"
