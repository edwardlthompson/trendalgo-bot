"""Deterministic long-only backtesting engine for Sprint 2.1."""

from __future__ import annotations

from typing import Optional

import pandas as pd

from .models import BacktestConfig, BacktestResult, BuyHoldResult, Trade


def _validate_frame(frame: pd.DataFrame) -> None:
    required_columns = {"open", "high", "low", "close", "volume"}
    if frame is None or frame.empty:
        raise ValueError("Input OHLCV frame is empty")
    if set(frame.columns) != required_columns:
        raise ValueError("Input OHLCV frame must include open/high/low/close/volume")


def _stake_notional(config: BacktestConfig, free_cash: float) -> float:
    """Cash committed to one entry. all_in commits all of it, so the golden path is unchanged."""
    if config.stake_mode == "fixed_usd":
        return min(float(config.stake_value or 0.0), free_cash)
    if config.stake_mode == "percent":
        return free_cash * float(config.stake_value or 0.0) / 100.0
    return free_cash


def _with_reserve(proceeds: float, reserve: float) -> float:
    """Free cash after a close. A zero reserve returns the proceeds unchanged (all_in path)."""
    return proceeds if reserve == 0.0 else proceeds + reserve


def run_backtest(
    frame: pd.DataFrame,
    buy_signals: pd.Series,
    sell_signals: Optional[pd.Series] = None,
    config: Optional[BacktestConfig] = None,
) -> BacktestResult:
    """Run deterministic long-only backtest with trailing stop and fees.

    The bar loop reads plain Python lists and hoisted config values. Every float
    expression keeps the original operation order, so results stay bit-identical
    (pinned by tests/test_lts_vendor/test_engine_golden.py).
    """
    _validate_frame(frame)

    if config is None:
        config = BacktestConfig()

    aligned_buy = buy_signals.reindex(frame.index).fillna(False).astype(bool)
    aligned_sell = (
        sell_signals.reindex(frame.index).fillna(False).astype(bool)
        if sell_signals is not None
        else pd.Series(False, index=frame.index)
    )

    index = frame.index
    close_values: list[float] = frame["close"].astype(float).tolist()
    high_values: list[float] = frame["high"].astype(float).tolist()
    low_values: list[float] = frame["low"].astype(float).tolist()
    buy_values: list[bool] = aligned_buy.tolist()
    sell_values: list[bool] = aligned_sell.tolist()

    starting_capital = config.starting_capital
    side_fee_rate = config.side_fee_rate
    take_profit_pct = config.take_profit_pct
    trailing_tp_pct = config.trailing_take_profit_pct
    trailing_sl_pct = config.trailing_stop_loss_pct
    trailing_sl_on = config.trailing_stop_enabled

    first_timestamp = index[0]
    first_close = close_values[0]

    entry_notional = _stake_notional(config, float(starting_capital))
    entry_fee = entry_notional * side_fee_rate
    net_to_asset = entry_notional - entry_fee

    cash = 0.0
    position_qty = (net_to_asset / first_close) if first_close > 0 and net_to_asset > 0 else 0.0
    # Free cash the stake leaves idle while the position is open (0.0 under all_in).
    reserve_cash = (float(starting_capital) - entry_notional) if position_qty > 0 else 0.0
    entry_price = first_close if position_qty > 0 else 0.0
    highest_price = first_close if position_qty > 0 else 0.0
    entry_time = first_timestamp if position_qty > 0 else None

    trades: list[Trade] = []
    previous_buy_signal = buy_values[0] if buy_values else False

    for position in range(len(close_values)):
        close_price = close_values[position]
        high_price = high_values[position]
        low_price = low_values[position]
        buy_signal = buy_values[position]
        sell_signal = sell_values[position]
        exited_this_bar = False
        new_buy_edge = buy_signal and not previous_buy_signal

        # Initial position is entered at first bar close; do not evaluate exits on same bar.
        if position == 0 and position_qty > 0:
            previous_buy_signal = buy_signal
            continue

        if position_qty > 0:
            if high_price > highest_price:
                highest_price = high_price

            stop_hit = False
            effective_exit: float | None = None
            exit_reason: str | None = None

            # 1. Hard take profit (only when no trailing take profit is configured)
            if take_profit_pct > 0 and trailing_tp_pct == 0.0:
                tp_price = entry_price * (1 + take_profit_pct / 100.0)
                if high_price >= tp_price:
                    stop_hit = True
                    effective_exit = tp_price
                    exit_reason = "take_profit"

            # 2. Trailing take profit
            elif take_profit_pct > 0 and trailing_tp_pct > 0:
                activation_price = entry_price * (1 + take_profit_pct / 100.0)
                if highest_price >= activation_price:
                    ttp_price = highest_price * (1 - trailing_tp_pct / 100.0)
                    if low_price <= ttp_price:
                        stop_hit = True
                        effective_exit = ttp_price
                        exit_reason = "trailing_take_profit"

            # 3. Trailing stop loss (off when trailing_stop_enabled is False)
            if not stop_hit and trailing_sl_on and trailing_sl_pct > 0:
                tsl_price = highest_price * (1 - trailing_sl_pct / 100.0)
                if low_price <= tsl_price:
                    stop_hit = True
                    effective_exit = tsl_price
                    exit_reason = "trailing_stop_loss"

            # 4. Sell signal
            if not stop_hit and sell_signal:
                stop_hit = True
                effective_exit = close_price
                exit_reason = "sell_signal"

            if stop_hit:
                if effective_exit is None:
                    effective_exit = close_price
                exit_notional = position_qty * effective_exit
                exit_fee = exit_notional * side_fee_rate
                proceeds = exit_notional - exit_fee
                cash = _with_reserve(proceeds, reserve_cash)
                reserve_cash = 0.0
                invested_notional = position_qty * entry_price + entry_fee
                pnl_pct = (
                    ((proceeds - invested_notional) / invested_notional * 100.0)
                    if invested_notional > 0
                    else 0.0
                )

                trades.append(
                    Trade(
                        entry_time=str(entry_time),
                        entry_price=entry_price,
                        entry_fee=entry_fee,
                        quantity=position_qty,
                        exit_time=str(index[position]),
                        exit_price=effective_exit,
                        exit_fee=exit_fee,
                        pnl_dollars=(position_qty * effective_exit - exit_fee) - invested_notional,
                        pnl_pct=pnl_pct,
                        exit_reason=exit_reason or "unknown",
                    )
                )

                position_qty = 0.0
                entry_price = 0.0
                entry_fee = 0.0
                highest_price = 0.0
                entry_time = None
                exited_this_bar = True

        if position_qty == 0 and new_buy_edge and not exited_this_bar:
            entry_notional = _stake_notional(config, cash)
            entry_fee = entry_notional * side_fee_rate
            net_to_asset = entry_notional - entry_fee
            if net_to_asset > 0 and close_price > 0:
                position_qty = net_to_asset / close_price
                entry_price = close_price
                highest_price = close_price
                entry_time = index[position]
                reserve_cash = cash - entry_notional
                cash = 0.0

        previous_buy_signal = buy_signal

    if position_qty > 0:
        final_close = close_values[-1]
        exit_notional = position_qty * final_close
        exit_fee = exit_notional * side_fee_rate
        proceeds = exit_notional - exit_fee
        cash = _with_reserve(proceeds, reserve_cash)

        invested_notional = position_qty * entry_price + entry_fee
        pnl_pct = (
            ((proceeds - invested_notional) / invested_notional * 100.0)
            if invested_notional > 0
            else 0.0
        )
        trades.append(
            Trade(
                entry_time=str(entry_time),
                entry_price=entry_price,
                entry_fee=entry_fee,
                quantity=position_qty,
                exit_time=str(index[-1]),
                exit_price=final_close,
                exit_fee=exit_fee,
                pnl_dollars=(position_qty * final_close - exit_fee) - invested_notional,
                pnl_pct=pnl_pct,
                exit_reason="end_of_data",
            )
        )

    final_equity = float(cash)
    net_pct = ((final_equity - starting_capital) / starting_capital) * 100.0
    wins = sum(1 for trade in trades if trade.pnl_dollars > 0)
    win_pct = (wins / len(trades) * 100.0) if trades else 0.0

    return BacktestResult(
        final_equity=final_equity,
        net_pct=net_pct,
        total_trades=len(trades),
        win_pct=win_pct,
        trades=trades,
    )


def compute_buy_and_hold(
    frame: pd.DataFrame, config: Optional[BacktestConfig] = None
) -> BuyHoldResult:
    """Compute buy-and-hold baseline from first close to last close with identical fee model."""
    _validate_frame(frame)

    if config is None:
        config = BacktestConfig()

    entry_price = float(frame.iloc[0]["close"])
    exit_price = float(frame.iloc[-1]["close"])

    entry_fee = config.starting_capital * config.side_fee_rate
    quantity = (config.starting_capital - entry_fee) / entry_price

    exit_notional = quantity * exit_price
    exit_fee = exit_notional * config.side_fee_rate
    final_equity = exit_notional - exit_fee

    net_pct = ((final_equity - config.starting_capital) / config.starting_capital) * 100.0

    return BuyHoldResult(
        final_equity=final_equity,
        net_pct=net_pct,
        entry_price=entry_price,
        exit_price=exit_price,
    )
