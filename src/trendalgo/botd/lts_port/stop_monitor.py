"""1-minute stop monitor for open positions (L1). It polls over REST and makes no call while flat."""

from __future__ import annotations

from collections.abc import Callable

import pandas as pd

from trendalgo.botd.lts_port.bar import Bar
from trendalgo.botd.lts_port.trader import StreamingTrader
from trendalgo.lts_vendor.backtesting.models import Trade

MIN_POLL_S = 15
MAX_POLL_S = 30


class StopMonitor:
    """Polls the forming 1-minute candle while a position is open. It exits on stops only."""

    def __init__(self, trader: StreamingTrader, *, interval_s: int = MAX_POLL_S) -> None:
        if not MIN_POLL_S <= interval_s <= MAX_POLL_S:
            raise ValueError(f"interval_s must be between {MIN_POLL_S} and {MAX_POLL_S}")
        self.trader = trader
        self.interval = pd.Timedelta(seconds=interval_s)
        self._last_poll: pd.Timestamp | None = None

    def due(self, now: pd.Timestamp) -> bool:
        """True only while a position is open and the poll interval has passed."""
        if self.trader.state.position_qty <= 0:
            return False
        return self._last_poll is None or now - self._last_poll >= self.interval

    def poll(self, fetch: Callable[[], Bar | None], now: pd.Timestamp) -> Trade | None:
        """One REST poll for the forming minute. `fetch` is the injected REST call."""
        if not self.due(now):
            return None
        self._last_poll = now
        forming = fetch()
        if forming is None:
            return None
        return self.trader.on_intrabar(forming)
