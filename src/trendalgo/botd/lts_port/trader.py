"""Closed-bar streaming port of the LTS trade loop (ADR-0016; L1, L3, L4, L5, L7, L8).

It mirrors engine.run_backtest bar for bar, but takes one closed bar at a time, so the host can run
what was backtested. Between closes, on_intrabar checks stops only (L1). The test-only bar-0 entry
(L3) exists so trade lists can match the engine. Live never sets it: a live host starts flat.
"""

from __future__ import annotations

from trendalgo.botd.lts_port.bar import Bar
from trendalgo.botd.lts_port.sizing import stake_notional, with_reserve
from trendalgo.botd.lts_port.state import PortState
from trendalgo.botd.lts_port.stops import first_exit
from trendalgo.lts_vendor.backtesting.models import BacktestConfig, Trade


class StreamingTrader:
    """One closed bar at a time. The host persists `self.state` between bars."""

    def __init__(
        self,
        config: BacktestConfig,
        *,
        warmup_bars: int,
        state: PortState | None = None,
        test_only_bar0_entry: bool = False,
    ) -> None:
        if warmup_bars < 1:
            raise ValueError("warmup_bars must be at least 1")
        self.config = config
        self.warmup_bars = warmup_bars
        self.test_only_bar0_entry = test_only_bar0_entry
        # A fresh state starts flat with the starting capital as free cash. A restored one keeps its own.
        self.state = state if state is not None else PortState(cash=float(config.starting_capital))

    @property
    def warmup_progress(self) -> float:
        """Share of the warm-up history seen so far, from 0.0 to 1.0 (L7 status)."""
        return min(1.0, self.state.bars_seen / self.warmup_bars)

    def on_closed_bar(self, bar_index: int, bar: Bar, *, buy: bool, sell: bool) -> list[Trade]:
        """Apply one closed bar and return the trades it closed. A replayed bar changes nothing."""
        st = self.state
        if bar_index < st.bars_seen:
            return []
        if bar_index != st.bars_seen:
            raise ValueError(f"bar {bar_index} is out of order; expected bar {st.bars_seen}")
        if bar_index == 0 and self.test_only_bar0_entry:
            st.cash = float(self.config.starting_capital)
            self._enter(bar)
            if st.position_qty <= 0:
                raise ValueError("test bar-0 entry needs a positive first close")
            st.previous_buy = buy
            st.bars_seen = 1
            return []
        previous = buy if bar_index == 0 else st.previous_buy  # engine: no edge on bar 0
        rising_edge = buy and not previous
        closed: list[Trade] = []
        if st.position_qty > 0:
            trade = self._exit_if_hit(bar, bar_index, sell)
            if trade is not None:
                closed.append(trade)
        exited_here = st.exited_on_bar == bar_index
        warm = bar_index + 1 >= self.warmup_bars
        if st.position_qty == 0 and rising_edge and not exited_here and warm:
            self._enter(bar)
        st.previous_buy = buy
        st.bars_seen = bar_index + 1
        return closed

    def on_intrabar(self, forming: Bar) -> Trade | None:
        """Stop check on the forming bar between closes (L1). It exits only; no entries, no signals."""
        if self.state.position_qty <= 0:
            return None
        return self._exit_if_hit(forming, self.state.bars_seen, sell=False)

    def flatten(self, bar: Bar, bar_index: int) -> list[Trade]:
        """Backtest end-of-data close at the last close. Live exits come from stops and signals."""
        if self.state.position_qty <= 0:
            return []
        return [self._close(bar, bar_index, bar.close, "end_of_data")]

    def _enter(self, bar: Bar) -> None:
        st, config = self.state, self.config
        notional = stake_notional(config, st.cash)
        fee = notional * config.side_fee_rate
        net = notional - fee
        if net > 0 and bar.close > 0:
            st.position_qty = net / bar.close
            st.entry_price = bar.close
            st.entry_fee = fee
            st.highest_price = bar.close
            st.entry_time = str(bar.timestamp)
            st.reserve_cash = st.cash - notional
            st.cash = 0.0

    def _exit_if_hit(self, bar: Bar, bar_index: int, sell: bool) -> Trade | None:
        st = self.state
        if bar.high > st.highest_price:
            st.highest_price = bar.high
        hit = first_exit(st, self.config, bar, sell)
        if hit is None:
            return None
        price, reason = hit
        return self._close(bar, bar_index, price, reason)

    def _close(self, bar: Bar, bar_index: int, price: float, reason: str) -> Trade:
        st, rate = self.state, self.config.side_fee_rate
        exit_notional = st.position_qty * price
        exit_fee = exit_notional * rate
        proceeds = exit_notional - exit_fee
        st.cash = with_reserve(proceeds, st.reserve_cash)
        st.reserve_cash = 0.0
        invested = st.position_qty * st.entry_price + st.entry_fee
        pnl_pct = ((proceeds - invested) / invested * 100.0) if invested > 0 else 0.0
        trade = Trade(
            entry_time=str(st.entry_time),
            entry_price=st.entry_price,
            entry_fee=st.entry_fee,
            quantity=st.position_qty,
            exit_time=str(bar.timestamp),
            exit_price=price,
            exit_fee=exit_fee,
            pnl_dollars=(st.position_qty * price - exit_fee) - invested,
            pnl_pct=pnl_pct,
            exit_reason=reason,
        )
        st.position_qty = 0.0
        st.entry_price = 0.0
        st.entry_fee = 0.0
        st.highest_price = 0.0
        st.entry_time = None
        st.exited_on_bar = bar_index  # L4 exit flag: no re-entry on the same bar
        return trade
