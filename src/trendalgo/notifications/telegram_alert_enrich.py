"""Attach Results-parity OHLC + hold trades to Telegram enter coins."""

from __future__ import annotations

from typing import Any

from trendalgo.device.scan_stake import DEVICE_SCAN_STAKE_USD
from trendalgo.device.scanner_chart_trades import regions_for_strategy, resolve_ohlcv_frame

_SKIP = frozenset({"B&H", "Oracle max"})
_OHLC_MAX = 240


def enrich_enter_coin(coin: dict[str, Any]) -> dict[str, Any]:
    """Copy strategy table fields and attach real OHLC + alert_trades (fail soft)."""
    out = dict(coin)
    _stamp_strategy_table(out)
    best = _best_tradable(out)
    if best is None:
        return out
    tf = str(best.get("timeframe") or "1h")
    try:
        frame = resolve_ohlcv_frame(out, timeframe=tf, for_overlay=True)
    except Exception:  # noqa: BLE001 — network/cache; keep caption-only path
        return out
    if frame is None or getattr(frame, "empty", True) or len(frame) < 2:
        return out
    window = frame.iloc[-_OHLC_MAX:] if len(frame) > _OHLC_MAX else frame
    try:
        regions = regions_for_strategy(window, best, stake_usd=DEVICE_SCAN_STAKE_USD)
    except Exception:  # noqa: BLE001
        regions = []
    out["ohlc_1h"] = [
        [float(o), float(h), float(lo), float(c)]
        for o, h, lo, c in zip(
            window["open"].tolist(),
            window["high"].tolist(),
            window["low"].tolist(),
            window["close"].tolist(),
            strict=False,
        )
    ]
    out["alert_trades"] = _trades_from_regions(regions, window)
    ind = str(best.get("indicator") or best.get("name") or "")
    out["best_bt"] = f"{ind} {tf}".strip()
    return out


def _stamp_strategy_table(coin: dict[str, Any]) -> None:
    raw = (
        coin.get("backtest_top_strategies") or coin.get("strategies") or coin.get("top_strategies")
    )
    rows = [r for r in raw if isinstance(r, dict)] if isinstance(raw, list) else []
    if not rows:
        return
    ranked = sorted(
        (r for r in rows if str(r.get("indicator") or "") not in _SKIP),
        key=lambda r: float(r.get("net_pct") or float("-inf")),
        reverse=True,
    )
    coin["strategies"] = [
        {
            "name": str(r.get("indicator") or r.get("name") or "?"),
            "timeframe": str(r.get("timeframe") or "—"),
            "net_pct": r.get("net_pct"),
            "trades": r.get("trades"),
            "win_pct": r.get("win_pct") or r.get("win_rate"),
        }
        for r in ranked[:5]
    ]
    bh = coin.get("backtest_buy_hold") or coin.get("buy_hold")
    if isinstance(bh, dict):
        coin["buy_hold"] = {
            "timeframe": str(bh.get("timeframe") or "—"),
            "net_pct": bh.get("net_pct"),
        }


def _best_tradable(coin: dict[str, Any]) -> dict[str, Any] | None:
    raw = coin.get("backtest_top_strategies") or coin.get("strategies") or []
    rows = [r for r in raw if isinstance(r, dict)] if isinstance(raw, list) else []
    candidates = [
        r
        for r in rows
        if str(r.get("indicator") or r.get("name") or "") not in _SKIP
        and not str(r.get("skip_reason") or "").strip()
    ]
    if not candidates:
        return None
    candidates.sort(key=lambda r: float(r.get("net_pct") or float("-inf")), reverse=True)
    return candidates[0]


def _trades_from_regions(regions: list[dict[str, Any]], frame: Any) -> list[dict[str, Any]]:
    index = list(frame.index)
    n = len(index)
    closes = [float(x) for x in frame["close"].tolist()]
    trades: list[dict[str, Any]] = []
    for reg in regions:
        try:
            ep, xp = float(reg["entry_price"]), float(reg["exit_price"])
            pnl = float(reg.get("pnl_pct") or 0.0)
        except (KeyError, TypeError, ValueError):
            continue
        ei = _coerce_index(reg.get("entry_index"), n)
        xi = _coerce_index(reg.get("exit_index"), n)
        if ei is None:
            ei = _bar_index(reg.get("entry_time"), index, closes, ep)
        if xi is None:
            xi = _bar_index(reg.get("exit_time"), index, closes, xp)
        if ei is None or xi is None:
            continue
        if xi <= ei:
            xi = min(ei + 1, n - 1)
        trades.append(
            {
                "entry_index": int(ei),
                "exit_index": int(xi),
                "entry_price": ep,
                "exit_price": xp,
                "pnl_pct": pnl,
            }
        )
    return trades


def _coerce_index(raw: object, n: int) -> int | None:
    if isinstance(raw, bool) or not isinstance(raw, (int, float, str)):
        return None
    try:
        i = int(raw)
    except (TypeError, ValueError):
        return None
    return i if 0 <= i < n else None


def _bar_index(stamp: object, index: list[Any], closes: list[float], price: float) -> int | None:
    if stamp is not None and stamp in index:
        try:
            return index.index(stamp)
        except ValueError:
            pass
    if not closes:
        return None
    return min(range(len(closes)), key=lambda i: abs(closes[i] - price))
