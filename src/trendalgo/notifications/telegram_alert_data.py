"""OHLC / trade / strategy table extraction for Telegram alert images."""

from __future__ import annotations

from typing import Any

Ohlc = tuple[float, float, float, float]


def ohlc_from_coin(coin: dict[str, Any]) -> list[Ohlc]:
    for key in ("ohlc_1h", "ohlc", "candles"):
        raw = coin.get(key)
        if isinstance(raw, list) and raw and isinstance(raw[0], (list, tuple)) and len(raw[0]) >= 4:
            out: list[Ohlc] = []
            for row in raw:
                try:
                    out.append((float(row[0]), float(row[1]), float(row[2]), float(row[3])))
                except (TypeError, ValueError, IndexError):
                    continue
            if len(out) >= 2:
                return out
    closes: list[float] = []
    for key in ("spark_closes_7d", "chart_closes_1h", "closes_7d", "closes", "spark_closes_30d"):
        raw = coin.get(key)
        if not isinstance(raw, list) or len(raw) < 2:
            continue
        for item in raw:
            try:
                closes.append(float(item))
            except (TypeError, ValueError):
                continue
        if len(closes) >= 2:
            break
        closes = []
    out2: list[Ohlc] = []
    prev = closes[0] if closes else 0.0
    for c in closes:
        o = prev
        out2.append((o, max(o, c), min(o, c), c))
        prev = c
    return out2


def trades_from_coin(coin: dict[str, Any]) -> list[dict[str, Any]]:
    for key in ("alert_trades", "best_bt_trades", "trades"):
        raw = coin.get(key)
        if isinstance(raw, list) and raw:
            return [t for t in raw if isinstance(t, dict)]
    return []


def strategy_table_rows(coin: dict[str, Any]) -> list[list[str]]:
    header = ["Indicator", "TF", "Net %", "Trades", "Win %"]
    body: list[list[str]] = []
    rows = coin.get("strategies") or coin.get("top_strategies") or []
    if isinstance(rows, list):
        for row in rows[:5]:
            if not isinstance(row, dict):
                continue
            body.append(
                [
                    str(row.get("name") or row.get("indicator") or "?")[:18],
                    str(row.get("timeframe") or row.get("tf") or "—"),
                    _pct(row.get("net_pct") or row.get("pnl_pct")),
                    str(row.get("trades") or "—"),
                    _pct(row.get("win_pct") or row.get("win_rate")),
                ]
            )
    bh = coin.get("buy_hold") or coin.get("bh") or {}
    if isinstance(bh, dict) and bh:
        body.append(
            [
                "B&H",
                str(bh.get("timeframe") or "—"),
                _pct(bh.get("net_pct") or bh.get("pnl_pct")),
                "—",
                "—",
            ]
        )
    elif not body:
        best = coin.get("best_bt")
        if best:
            body.append([str(best)[:18], "—", "—", "—", "—"])
    return [header, *body] if body else [header, ["—", "—", "no BT yet", "—", "—"]]


def _pct(raw: object) -> str:
    try:
        return f"{float(raw):+.1f}%"  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return "—"
