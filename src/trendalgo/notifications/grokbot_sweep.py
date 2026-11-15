"""LTS backtest sweep_complete webhook payload (advisory; does not change ranking)."""

from __future__ import annotations

from typing import Any

from trendalgo.notifications.grokbot_payload import envelope


def overfitting_flags(row: dict[str, Any]) -> list[str]:
    flags: list[str] = []
    trades = _num(row.get("trades") if "trades" in row else row.get("Trades"))
    win = _num(row.get("win_pct") if "win_pct" in row else row.get("Win %"))
    conf = _num(row.get("confidence_score"))
    if trades < 8:
        flags.append("thin_sample")
    if win >= 80 and trades < 20:
        flags.append("high_win_thin_sample")
    if conf and conf < 35:
        flags.append("low_confidence")
    period = row.get("period_concentration") or row.get("trade_day_share")
    if period is not None and _num(period) >= 0.6:
        flags.append("period_concentration")
    return flags


def sweep_digest(coins: list[dict[str, Any]]) -> dict[str, Any]:
    top: list[dict[str, Any]] = []
    flags_out: list[dict[str, Any]] = []
    for coin in coins[:20]:
        symbol = str(coin.get("symbol") or coin.get("pair") or "")
        rows = coin.get("backtest_top_strategies") or []
        if not isinstance(rows, list) or not rows or not isinstance(rows[0], dict):
            continue
        best = rows[0]
        trades = _num(best.get("trades") if "trades" in best else best.get("Trades"))
        win = _num(best.get("win_pct") if "win_pct" in best else best.get("Win %"))
        net = _num(best.get("net_pct") if "net_pct" in best else best.get("Net %"))
        item = {
            "symbol": symbol,
            "strategy": str(best.get("indicator") or best.get("id") or best.get("name") or ""),
            "trades": trades,
            "win_pct": win,
            "net_pct": net,
            "confidence": _num(best.get("confidence_score")),
        }
        top.append(item)
        flags = overfitting_flags(best)
        if flags:
            flags_out.append({"symbol": symbol, "flags": flags, "trades": trades, "win_pct": win})
    return {
        "top": top[:10],
        "overfitting": flags_out[:10],
        "oos_split": None,
        "coin_count": len(coins),
    }


def emit_sweep_complete(
    coins: list[dict[str, Any]], summary: dict[str, Any] | None = None
) -> dict[str, Any]:
    from trendalgo.notifications.grokbot import emit

    del summary
    digest = sweep_digest(coins)
    text = (
        f"LTS sweep complete: {digest['coin_count']} coins, "
        f"{len(digest['top'])} ranked, {len(digest['overfitting'])} overfitting flags"
    )
    payload = envelope(event_type="sweep_complete", reason=text)
    payload["gains"] = digest
    return emit(payload)


def _num(raw: object) -> float:
    if raw is None or raw == "-":
        return 0.0
    if isinstance(raw, bool):
        return 0.0
    if isinstance(raw, (int, float)):
        return float(raw)
    try:
        return float(str(raw).replace("%", ""))
    except ValueError:
        return 0.0
