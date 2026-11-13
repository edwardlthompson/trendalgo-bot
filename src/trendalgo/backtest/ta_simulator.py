"""Fee-aware long-only TA backtest simulator.

SIM-01: ``fill_offset`` (default 1) fills entries/signal exits at ``closes[i+offset]``.
Use ``fill_offset=0`` for legacy signal-bar parity. SIM-02: ``slippage_bps`` on both
sides; trailing stops trigger off bar low (long); gap-through uses worse of stop and
open. Known omissions: no funding, no min notional, no partial fills.
"""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from trendalgo.backtest.sim_fill import apply_entry_slip, apply_exit_slip, gap_through_long_exit
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
        "entry_index": int(entry_i),
        "exit_index": int(exit_i),
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
    fill_offset: int = 1,
    slippage_bps: float = 0.0,
) -> dict[str, Any]:
    closes = df["close"].to_numpy(dtype=float)
    opens = df["open"].to_numpy(dtype=float) if "open" in df.columns else closes
    highs = df["high"].to_numpy(dtype=float) if "high" in df.columns else closes
    lows = df["low"].to_numpy(dtype=float) if "low" in df.columns else closes
    fee_per_trade = fee.round_trip_taker_cost(stake_usd)
    tsl = max(0.0, trailing_stop_pct)
    offset = max(0, int(fill_offset))
    slip = max(0.0, float(slippage_bps))
    if not collect_trades:
        from trendalgo.backtest.sim_accel import pack_stats, simulate_arrays  # noqa: PLC0415

        gross, fees_paid, trades, wins, tsl_hits, open_n = simulate_arrays(
            closes,
            entries,
            exits,
            stake_usd=stake_usd,
            fee_per_trade=fee_per_trade,
            trailing_stop_pct=tsl,
            fill_offset=offset,
            slippage_bps=slip,
            opens=opens,
            highs=highs,
            lows=lows,
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
        fill_offset=offset,
        slippage_bps=slip,
        opens=opens,
        highs=highs,
        lows=lows,
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
    fill_offset: int = 0,
    slippage_bps: float = 0.0,
    opens: np.ndarray | None = None,
    highs: np.ndarray | None = None,
    lows: np.ndarray | None = None,
) -> dict[str, Any]:
    o_arr = opens if opens is not None else closes
    h_arr = highs if highs is not None else closes
    l_arr = lows if lows is not None else closes
    offset = max(0, int(fill_offset))
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
    pending_entry = 0
    pending_exit = 0
    trade_list: list[dict[str, Any]] = []

    def _close(exit_i: int, exit_px: float, *, tsl_exit: bool, open_exit: bool = False) -> None:
        nonlocal gross, fees_paid, trades, wins, tsl_hits, in_pos, entry_price, peak_price
        px = apply_exit_slip(exit_px, slippage_bps)
        if tsl_exit:
            tsl_hits += 1
        gross_pnl = stake_usd * ((px / entry_price) - 1.0) if entry_price else 0.0
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
                exit_i=exit_i,
                entry_price=entry_price,
                exit_price=px,
                net_pnl=net_pnl,
                stake_usd=stake_usd,
                tsl_exit=tsl_exit,
                open_exit=open_exit,
            )
        )
        in_pos = False
        entry_price = 0.0
        peak_price = 0.0

    for i in range(1, len(closes)):
        if pending_entry > 0 and not in_pos:
            pending_entry -= 1
            if pending_entry == 0:
                in_pos = True
                entry_price = apply_entry_slip(float(closes[i]), slippage_bps)
                entry_i = i
                peak_price = float(h_arr[i])
        if in_pos and pending_exit > 0:
            pending_exit -= 1
            if pending_exit == 0:
                _close(i, float(closes[i]), tsl_exit=False)
                continue
        if not in_pos and pending_entry == 0 and bool(entries[i]):
            if offset == 0:
                in_pos = True
                entry_price = apply_entry_slip(float(closes[i]), slippage_bps)
                entry_i = i
                peak_price = float(h_arr[i])
            else:
                pending_entry = offset
            continue
        if not in_pos or pending_exit > 0:
            continue
        peak_price = max(peak_price, float(h_arr[i]))
        stop_px = peak_price * (1.0 - tsl) if tsl > 0 else 0.0
        stop_hit = tsl > 0 and float(l_arr[i]) <= stop_px
        if stop_hit:
            fill = gap_through_long_exit(stop_px, float(o_arr[i]))
            _close(i, fill, tsl_exit=True)
            continue
        if bool(exits[i]):
            if offset == 0:
                _close(i, float(closes[i]), tsl_exit=False)
            else:
                pending_exit = offset
    if in_pos and entry_price:
        last = len(closes) - 1
        _close(last, float(closes[last]), tsl_exit=False, open_exit=True)
        open_trades = 1
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


# Min reverse move (percent of price) for zigzag densify on top of order-1 fractals.
ORACLE_ZIGZAG_MIN_MOVE_PCT = 0.25
# Hard cap so Secret Sauce search stays bounded on 30d/1h.
ORACLE_SWING_CAP = 500


def simulate_oracle_max_gain(
    df: pd.DataFrame,
    *,
    stake_usd: float,
    fee: ExchangeFeeSchedule,
) -> dict[str, Any] | None:
    """Long-only max gain: winners-only trough→peak on completed bars.

    Exits only when peak > entry and gross clears round-trip fees (perfect
    trough→peak baseline for Secret Sauce). Uses bar high/low at index ``i``
    only (no lookahead). Fees match buy-and-hold (fixed stake round-trip).
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
        # Winners-only: skip peaks at/below entry or fee-negative closes.
        if position is not None and kind == "H" and price > position[1]:
            entry_i, entry_px = position
            if idx <= entry_i:
                continue
            g = stake_usd * ((price / entry_px) - 1.0) if entry_px else 0.0
            f = fee.round_trip_taker_cost(stake_usd)
            if g <= f:
                continue
            net_t = g - f
            gross += g
            fees_paid += f
            trades += 1
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


def simulate_oracle_tradable_proxy(
    df: pd.DataFrame,
    swings: list[dict[str, Any]],
    *,
    stake_usd: float,
    fee: ExchangeFeeSchedule,
    fill_offset: int = 1,
) -> dict[str, Any] | None:
    """Same Oracle swing *labels*, fills at next-bar close (fee-on) — UX honesty proxy.

    Not a live strategy. Shows why HL ceiling Net % is not comparable to Sauce/TA.
    """
    n = len(df)
    if n < 3 or not swings:
        return None
    entries = np.zeros(n, dtype=bool)
    exits = np.zeros(n, dtype=bool)
    for trade in swings:
        try:
            e_i = int(trade.get("entry_index") or -1)
            x_i = int(trade.get("exit_index") or -1)
        except (TypeError, ValueError):
            continue
        if 0 <= e_i < n:
            entries[e_i] = True
        if 0 <= x_i < n:
            exits[x_i] = True
    if not entries.any() or not exits.any():
        return None
    return simulate_long_with_fees(
        df,
        entries,
        exits,
        stake_usd=stake_usd,
        fee=fee,
        fill_offset=fill_offset,
        collect_trades=False,
    )


def _fractal_swings(highs: Any, lows: Any) -> list[tuple[int, str, float]]:
    """Order-1 local trough (L) / peak (H) on completed bars (needs neighbors)."""
    n = len(highs)
    out: list[tuple[int, str, float]] = []
    for i in range(1, n - 1):
        lo = float(lows[i])
        hi = float(highs[i])
        if lo <= float(lows[i - 1]) and lo <= float(lows[i + 1]):
            out.append((i, "L", lo))
        if hi >= float(highs[i - 1]) and hi >= float(highs[i + 1]):
            out.append((i, "H", hi))
    return out


def _zigzag_swings(
    highs: Any,
    lows: Any,
    *,
    min_move_pct: float,
) -> list[tuple[int, str, float]]:
    """Pivots confirmed when reverse move clears ``min_move_pct`` of price."""
    n = len(highs)
    if n < 2 or min_move_pct <= 0:
        return []
    thr = min_move_pct / 100.0
    out: list[tuple[int, str, float]] = []
    # trend: 1 tracking high after rising, -1 tracking low after falling, 0 seek
    trend = 0
    extreme_i = 0
    extreme_px = float(lows[0])
    seed_hi = float(highs[0])
    for i in range(1, n):
        hi = float(highs[i])
        lo = float(lows[i])
        if trend == 0:
            if hi >= extreme_px * (1.0 + thr):
                trend = 1
                extreme_i, extreme_px = i, hi
            elif lo <= seed_hi * (1.0 - thr):
                trend = -1
                extreme_i, extreme_px = i, lo
            else:
                if lo < extreme_px:
                    extreme_i, extreme_px = i, lo
                if hi > seed_hi:
                    seed_hi = hi
            continue
        if trend == 1:
            if hi >= extreme_px:
                extreme_i, extreme_px = i, hi
            elif lo <= extreme_px * (1.0 - thr):
                out.append((extreme_i, "H", extreme_px))
                trend = -1
                extreme_i, extreme_px = i, lo
            continue
        if hi >= extreme_px * (1.0 + thr):
            out.append((extreme_i, "L", extreme_px))
            trend = 1
            extreme_i, extreme_px = i, hi
        elif lo <= extreme_px:
            extreme_i, extreme_px = i, lo
    return out


def _alternate_collapse(
    pivots: list[tuple[int, str, float]],
) -> list[tuple[int, str, float]]:
    """One pivot per bar; consecutive same-kind keep the extreme; L/H alternate."""
    by_index: dict[int, dict[str, float]] = {}
    for idx, kind, price in pivots:
        bucket = by_index.setdefault(idx, {})
        prev = bucket.get(kind)
        if prev is None:
            bucket[kind] = price
        elif kind == "L":
            bucket[kind] = min(prev, price)
        else:
            bucket[kind] = max(prev, price)
    ordered: list[tuple[int, str, float]] = []
    for idx in sorted(by_index):
        bucket = by_index[idx]
        if "L" in bucket and "H" in bucket:
            # Same bar cannot be both trough and peak — keep the farther extreme
            # from the prior pivot, else prefer L (oracle enters on troughs).
            if ordered:
                prev_px = ordered[-1][2]
                lo_d = abs(bucket["L"] - prev_px)
                hi_d = abs(bucket["H"] - prev_px)
                kind = "L" if lo_d >= hi_d else "H"
            else:
                kind = "L"
            ordered.append((idx, kind, bucket[kind]))
            continue
        kind = "L" if "L" in bucket else "H"
        ordered.append((idx, kind, bucket[kind]))
    collapsed: list[tuple[int, str, float]] = []
    for item in ordered:
        if not collapsed or collapsed[-1][1] != item[1]:
            collapsed.append(item)
            continue
        prev_i, prev_k, prev_p = collapsed[-1]
        if prev_k == "L":
            collapsed[-1] = item if item[2] <= prev_p else (prev_i, prev_k, prev_p)
        else:
            collapsed[-1] = item if item[2] >= prev_p else (prev_i, prev_k, prev_p)
    return collapsed


def _swing_points(
    highs: Any,
    lows: Any,
    *,
    min_move_pct: float = ORACLE_ZIGZAG_MIN_MOVE_PCT,
) -> list[tuple[int, str, float]]:
    """Fractal floor; zigzag when denser; alternate-collapse; capped."""
    fractal = _alternate_collapse(_fractal_swings(highs, lows))
    zigzag = _alternate_collapse(_zigzag_swings(highs, lows, min_move_pct=min_move_pct))
    # Floor = fractals; use zigzag only when it yields a denser alternating path.
    chosen = zigzag if len(zigzag) > len(fractal) else fractal
    if len(chosen) > ORACLE_SWING_CAP:
        return chosen[:ORACLE_SWING_CAP]
    return chosen


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
        region: dict[str, Any] = {
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
        if trade.get("entry_index") is not None:
            region["entry_index"] = trade.get("entry_index")
        if trade.get("exit_index") is not None:
            region["exit_index"] = trade.get("exit_index")
        regions.append(region)
    return regions


def _region_label(pnl_pct: object, tsl_exit: bool) -> str:
    try:
        pct = float(pnl_pct)  # type: ignore[arg-type]
        text = f"{pct:+.1f}%"
    except (TypeError, ValueError):
        text = "—"
    return f"{text} TSL" if tsl_exit else text
