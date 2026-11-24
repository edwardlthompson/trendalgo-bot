"""Chart surface payload: closes, OHLC candles, trade markers (AV-G-RES3)."""

from __future__ import annotations

from typing import Any


def _float_list(raw: object) -> list[float]:
    if not isinstance(raw, list):
        return []
    out: list[float] = []
    for x in raw:
        try:
            out.append(float(x))
        except (TypeError, ValueError):
            continue
    return out


def _ohlc_from_coin(coin: dict[str, Any], *, limit: int = 96) -> list[dict[str, float | int]]:
    raw = coin.get("chart_ohlc_1h")
    if not isinstance(raw, list):
        return []
    bars: list[dict[str, float | int]] = []
    for item in raw[-limit:]:
        if not isinstance(item, dict):
            continue
        try:
            bars.append(
                {
                    "t": int(item.get("t") or 0),
                    "o": float(item["o"]),
                    "h": float(item["h"]),
                    "l": float(item["l"]),
                    "c": float(item["c"]),
                }
            )
        except (KeyError, TypeError, ValueError):
            continue
    return bars


def _trade_markers_from_coin(coin: dict[str, Any]) -> list[dict[str, Any]]:
    rows = coin.get("backtest_top_strategies")
    if not isinstance(rows, list) or not rows:
        return []
    top = rows[0] if isinstance(rows[0], dict) else None
    if top is None:
        return []
    trades = top.get("trades")
    if not isinstance(trades, list):
        return []
    markers: list[dict[str, Any]] = []
    for trade in trades:
        if not isinstance(trade, dict):
            continue
        try:
            if trade.get("entry_time") is not None and trade.get("entry_price") is not None:
                markers.append(
                    {
                        "side": "entry",
                        "t": str(trade.get("entry_time") or ""),
                        "price": float(trade["entry_price"]),
                    }
                )
            if trade.get("exit_time") is not None and trade.get("exit_price") is not None:
                markers.append(
                    {
                        "side": "exit",
                        "t": str(trade.get("exit_time") or ""),
                        "price": float(trade["exit_price"]),
                    }
                )
        except (TypeError, ValueError):
            continue
    return markers


def chart_summary_from_coin(coin: dict[str, Any], *, window_key: str = "30d") -> dict[str, Any]:
    wkey = "7d" if str(window_key).strip().lower().startswith("7") else "30d"
    if wkey == "7d":
        ohlc = _ohlc_from_coin(coin, limit=168)
        series = _float_list(coin.get("spark_closes_7d") or coin.get("closes_7d"))
        if not series:
            series = _float_list(
                coin.get("chart_closes") or coin.get("chart_closes_1h") or coin.get("closes_1h")
            )[-168:]
        if not series and ohlc:
            series = [float(b["c"]) for b in ohlc]
        window = series[-168:]
    else:
        ohlc = _ohlc_from_coin(coin, limit=720)
        series = _float_list(
            coin.get("chart_closes") or coin.get("chart_closes_1h") or coin.get("closes_1h")
        )[-720:]
        if not series:
            series = _float_list(coin.get("spark_closes_30d") or coin.get("closes_30d"))
        if not series and ohlc:
            series = [float(b["c"]) for b in ohlc]
        window = series[-720:]
    last = window[-1] if window else None
    first = window[0] if window else None
    hi = max(window) if window else None
    lo = min(window) if window else None
    change = None
    if first is not None and last is not None and first != 0:
        change = ((last - first) / abs(first)) * 100.0
    candles = [
        {
            "i": i + 1,
            "close": close,
            "from_high_pct": None if hi is None or hi == 0 else ((close - hi) / abs(hi)) * 100.0,
        }
        for i, close in enumerate(window)
    ]
    return {
        "pair": str(coin.get("pair") or ""),
        "window": "7D" if wkey == "7d" else "30D",
        "bars": len(series),
        "last": last,
        "high": hi,
        "low": lo,
        "change_pct": change,
        "closes": window,
        "candles": candles,
        "ohlc": ohlc,
        "trades": _trade_markers_from_coin(coin),
    }
