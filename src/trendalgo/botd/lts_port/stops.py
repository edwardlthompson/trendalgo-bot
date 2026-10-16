"""Exit rules of the streaming port, in the engine's order (take profit, trailing TP, trailing SL, sell)."""

from __future__ import annotations

from trendalgo.botd.lts_port.bar import Bar
from trendalgo.botd.lts_port.state import PortState
from trendalgo.lts_vendor.backtesting.models import BacktestConfig


def first_exit(
    state: PortState, config: BacktestConfig, bar: Bar, sell: bool
) -> tuple[float, str] | None:
    """The first exit rule that fires, as (price, reason). None when the position holds."""
    tp, trailing_tp = config.take_profit_pct, config.trailing_take_profit_pct
    if tp > 0 and trailing_tp == 0.0:
        tp_price = state.entry_price * (1 + tp / 100.0)
        if bar.high >= tp_price:
            return tp_price, "take_profit"
    elif tp > 0 and trailing_tp > 0:
        if state.highest_price >= state.entry_price * (1 + tp / 100.0):
            ttp_price = state.highest_price * (1 - trailing_tp / 100.0)
            if bar.low <= ttp_price:
                return ttp_price, "trailing_take_profit"
    if config.trailing_stop_enabled and config.trailing_stop_loss_pct > 0:
        tsl_price = state.highest_price * (1 - config.trailing_stop_loss_pct / 100.0)
        if bar.low <= tsl_price:
            return tsl_price, "trailing_stop_loss"
    if sell:
        return bar.close, "sell_signal"
    return None
