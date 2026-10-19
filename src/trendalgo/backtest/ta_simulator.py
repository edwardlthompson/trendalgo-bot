"""Fee-aware long-only TA backtest simulator."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from trendalgo.exchanges.fees import ExchangeFeeSchedule


def _bar_time(df: pd.DataFrame, index: int) -> str:
    stamp = df.index[index]
    iso = getattr(stamp, "isoformat", None)
    if callable(iso):
        return str(iso())
    return str(stamp)


def _trade_record(
    df: pd.DataFrame,
    *,
    entry_i: int,
    exit_i: int,
    entry_price: float,
    exit_price: float,
    net_pnl: float,
    stake_usd: float,
    tsl_exit: bool,
    open_exit: bool = False,
) -> dict[str, Any]:
    price_pct = ((exit_price / entry_price) - 1.0) * 100.0 if entry_price else 0.0
    net_pct = (net_pnl / stake_usd) * 100.0 if stake_usd else price_pct
    if open_exit:
        reason = "open"
    elif tsl_exit:
        reason = "tsl"
    else:
        reason = "signal"
    return {
        "entry_time": _bar_time(df, entry_i),
        "exit_time": _bar_time(df, exit_i),
        "entry_price": float(entry_price),
        "exit_price": float(exit_price),
        "net_pnl": round(net_pnl, 4),
        "pnl_pct": round(net_pct, 2),
        "tsl_exit": bool(tsl_exit),
        "open_exit": bool(open_exit),
        "exit_reason": reason,
    }


def simulate_long_with_fees(
    df: pd.DataFrame,
    entries: np.ndarray,
    exits: np.ndarray,
    *,
    stake_usd: float,
    fee: ExchangeFeeSchedule,
    trailing_stop_pct: float = 0.0,
    collect_trades: bool = False,
) -> dict[str, Any]:
    closes = df["close"].to_numpy(dtype=float)
    fee_per_trade = fee.round_trip_taker_cost(stake_usd)
    tsl = max(0.0, trailing_stop_pct)
    if not collect_trades:
        from trendalgo.backtest.sim_accel import pack_stats, simulate_arrays  # noqa: PLC0415

        gross, fees_paid, trades, wins, tsl_hits, open_n = simulate_arrays(
            closes,
            entries,
            exits,
            stake_usd=stake_usd,
            fee_per_trade=fee_per_trade,
            trailing_stop_pct=tsl,
        )
        return pack_stats((gross, fees_paid, trades, wins, tsl_hits, open_n, tsl), fee)
    return _simulate_collecting_trades(
        df,
        closes,
        entries,
        exits,
        stake_usd=stake_usd,
        fee=fee,
        fee_per_trade=fee_per_trade,
        tsl=tsl,
    )


def _simulate_collecting_trades(
    df: pd.DataFrame,
    closes: np.ndarray,
    entries: np.ndarray,
    exits: np.ndarray,
    *,
    stake_usd: float,
    fee: ExchangeFeeSchedule,
    fee_per_trade: float,
    tsl: float,
) -> dict[str, Any]:
    gross = 0.0
    fees_paid = 0.0
    trades = 0
    wins = 0
    tsl_hits = 0
    open_trades = 0
    in_pos = False
    entry_price = 0.0
    entry_i = 0
    peak_price = 0.0
    trade_list: list[dict[str, Any]] = []
    for i in range(1, len(closes)):
        if not in_pos and entries[i]:
            in_pos = True
            entry_price = closes[i]
            entry_i = i
            peak_price = entry_price
        elif in_pos:
            peak_price = max(peak_price, closes[i])
            stop_hit = tsl > 0 and closes[i] <= peak_price * (1.0 - tsl)
            if exits[i] or stop_hit:
                if stop_hit:
                    tsl_hits += 1
                gross_pnl = stake_usd * ((closes[i] / entry_price) - 1.0) if entry_price else 0.0
                net_pnl = gross_pnl - fee_per_trade
                gross += gross_pnl
                fees_paid += fee_per_trade
                trades += 1
                if net_pnl > 0:
                    wins += 1
                trade_list.append(
                    _trade_record(
                        df,
                        entry_i=entry_i,
                        exit_i=i,
                        entry_price=entry_price,
                        exit_price=float(closes[i]),
                        net_pnl=net_pnl,
                        stake_usd=stake_usd,
                        tsl_exit=stop_hit,
                    )
                )
                in_pos = False
                entry_price = 0.0
                peak_price = 0.0
    if in_pos and entry_price:
        gross_pnl = stake_usd * ((closes[-1] / entry_price) - 1.0)
        net_pnl = gross_pnl - fee_per_trade
        gross += gross_pnl
        fees_paid += fee_per_trade
        trades += 1
        open_trades = 1
        trade_list.append(
            _trade_record(
                df,
                entry_i=entry_i,
                exit_i=len(closes) - 1,
                entry_price=entry_price,
                exit_price=float(closes[-1]),
                net_pnl=net_pnl,
                stake_usd=stake_usd,
                tsl_exit=False,
                open_exit=True,
            )
        )
    closed = max(0, trades - open_trades)
    win_rate = (wins / closed) if closed else 0.0
    return {
        "gross_profit": round(gross, 4),
        "fees_paid": round(fees_paid, 4),
        "net_profit": round(gross - fees_paid, 4),
        "trades": trades,
        "wins": wins,
        "open_trades": open_trades,
        "tsl_hits": tsl_hits,
        "win_rate": round(win_rate, 4),
        "fee_taker_pct": fee.taker_pct,
        "trailing_stop_pct": tsl,
        "trade_list": trade_list,
    }


def simulate_buy_and_hold(
    df: pd.DataFrame,
    *,
    stake_usd: float,
    fee: ExchangeFeeSchedule,
) -> dict[str, Any] | None:
    if len(df) < 2:
        return None
    closes = df["close"].to_numpy(dtype=float)
    entry = float(closes[0])
    exit_p = float(closes[-1])
    if entry <= 0:
        return None
    gross_pnl = stake_usd * ((exit_p / entry) - 1.0)
    fee_paid = fee.round_trip_taker_cost(stake_usd)
    net = gross_pnl - fee_paid
    return {
        "strategy_id": "BUY_AND_HOLD",
        "timeframe": "ALL",
        "gross_profit": round(gross_pnl, 4),
        "fees_paid": round(fee_paid, 4),
        "net_profit": round(net, 4),
        "trades": 1,
        "wins": 1 if net > 0 else 0,
        "open_trades": 0,
        "tsl_hits": 0,
        "win_rate": 1.0 if net > 0 else 0.0,
        "fee_taker_pct": fee.taker_pct,
        "params": {},
        "trailing_stop_pct": 0.0,
        "phase": "baseline",
        "bar_count": len(df),
    }


def simulate_oracle_max_gain(
    df: pd.DataFrame,
    *,
    stake_usd: float,
    fee: ExchangeFeeSchedule,
) -> dict[str, Any] | None:
    """Long-only max gain: non-overlapping swing trough→peak on completed bars.

    Uses bar high/low only at index ``i`` (no lookahead past that bar). Fees match
    buy-and-hold (fixed stake round-trip per swing).
    """
    if len(df) < 3:
        return None
    highs = (
        df["high"].to_numpy(dtype=float)
        if "high" in df.columns
        else df["close"].to_numpy(dtype=float)
    )
    lows = (
        df["low"].to_numpy(dtype=float)
        if "low" in df.columns
        else df["close"].to_numpy(dtype=float)
    )
    swings = _swing_points(highs, lows)
    if not swings:
        return None
    gross = 0.0
    fees_paid = 0.0
    trades = 0
    wins = 0
    trade_list: list[dict[str, Any]] = []
    position: tuple[int, float] | None = None
    for idx, kind, price in swings:
        if position is None and kind == "L" and price > 0:
            position = (idx, price)
            continue
        if position is not None and kind == "H" and price > position[1]:
            entry_i, entry_px = position
            g = stake_usd * ((price / entry_px) - 1.0)
            f = fee.round_trip_taker_cost(stake_usd)
            net_t = g - f
            gross += g
            fees_paid += f
            trades += 1
            if net_t > 0:
                wins += 1
            trade_list.append(
                {
                    "entry_index": entry_i,
                    "exit_index": idx,
                    "entry_time": _bar_time(df, entry_i),
                    "exit_time": _bar_time(df, idx),
                    "entry_price": entry_px,
                    "exit_price": price,
                    "net_pnl": round(net_t, 4),
                    "pnl_pct": round(((price / entry_px) - 1.0) * 100.0, 4),
                    "exit_reason": "oracle_swing",
                }
            )
            position = None
    if trades == 0:
        return None
    net = gross - fees_paid
    return {
        "strategy_id": "ORACLE_MAX",
        "timeframe": "ALL",
        "gross_profit": round(gross, 4),
        "fees_paid": round(fees_paid, 4),
        "net_profit": round(net, 4),
        "trades": trades,
        "wins": wins,
        "open_trades": 0,
        "tsl_hits": 0,
        "win_rate": round(wins / trades, 4) if trades else 0.0,
        "fee_taker_pct": fee.taker_pct,
        "params": {},
        "trailing_stop_pct": 0.0,
        "phase": "baseline",
        "bar_count": len(df),
        "trade_list": trade_list,
        "oracle_swings": trade_list,
    }


def _swing_points(
    highs: Any,
    lows: Any,
) -> list[tuple[int, str, float]]:
    """Local trough (L) / peak (H) on completed bars only (needs neighbors)."""
    n = len(highs)
    out: list[tuple[int, str, float]] = []
    for i in range(1, n - 1):
        lo = float(lows[i])
        hi = float(highs[i])
        if lo <= float(lows[i - 1]) and lo <= float(lows[i + 1]):
            out.append((i, "L", lo))
        if hi >= float(highs[i - 1]) and hi >= float(highs[i + 1]):
            out.append((i, "H", hi))
    out.sort(key=lambda item: item[0])
    return out


def trade_hold_regions(trade_list: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Map simulator trade_list into chart highlight regions (green/red)."""
    regions: list[dict[str, Any]] = []
    for trade in trade_list:
        entry_px = float(trade.get("entry_price") or 0.0)
        exit_px = float(trade.get("exit_price") or 0.0)
        pnl = trade.get("net_pnl")
        profitable = float(pnl) >= 0 if pnl is not None else exit_px >= entry_px
        pnl_pct = trade.get("pnl_pct")
        if pnl_pct is None and entry_px:
            pnl_pct = ((exit_px / entry_px) - 1.0) * 100.0
        tsl_exit = bool(trade.get("tsl_exit"))
        regions.append(
            {
                "entry_time": trade.get("entry_time"),
                "exit_time": trade.get("exit_time"),
                "entry_price": entry_px,
                "exit_price": exit_px,
                "net_pnl": float(pnl) if pnl is not None else None,
                "pnl_pct": float(pnl_pct) if pnl_pct is not None else None,
                "tsl_exit": tsl_exit,
                "exit_reason": str(trade.get("exit_reason") or ("tsl" if tsl_exit else "signal")),
                "profitable": profitable,
                "label": _region_label(pnl_pct, tsl_exit),
            }
        )
    return regions


def _region_label(pnl_pct: object, tsl_exit: bool) -> str:
    try:
        pct = float(pnl_pct)  # type: ignore[arg-type]
        text = f"{pct:+.1f}%"
    except (TypeError, ValueError):
        text = "—"
    return f"{text} TSL" if tsl_exit else text
