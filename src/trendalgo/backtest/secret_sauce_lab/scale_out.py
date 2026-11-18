"""H — partial scale-out ladder helpers (fee-aware stub on full exit for now).

Full multi-leg sim is a follow-on; this module scores a 50% early-exit proxy by
exiting half the stake at mid-hold peak-confirm when available.
"""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from trendalgo.backtest.ta_simulator import simulate_long_with_fees
from trendalgo.exchanges.fees import ExchangeFeeSchedule


def scale_out_proxy_net(
    df: pd.DataFrame,
    entries: np.ndarray,
    exits: np.ndarray,
    *,
    fee: ExchangeFeeSchedule,
    stake_usd: float,
    trailing_stop_pct: float = 0.0,
) -> dict[str, Any]:
    """Compare full exit vs earlier exit (peak_confirm-like: exit shifted -2 bars)."""
    full = simulate_long_with_fees(
        df, entries, exits, stake_usd=stake_usd, fee=fee, trailing_stop_pct=trailing_stop_pct
    )
    early = np.zeros(len(df), dtype=bool)
    idxs = np.flatnonzero(exits)
    for i in idxs:
        j = max(0, int(i) - 2)
        early[j] = True
    half = simulate_long_with_fees(
        df, entries, early, stake_usd=stake_usd * 0.5, fee=fee, trailing_stop_pct=trailing_stop_pct
    )
    rest = simulate_long_with_fees(
        df, entries, exits, stake_usd=stake_usd * 0.5, fee=fee, trailing_stop_pct=trailing_stop_pct
    )
    blended = float(half.get("net_profit") or 0.0) + float(rest.get("net_profit") or 0.0)
    return {
        "full_net": float(full.get("net_profit") or 0.0),
        "scale_out_net": blended,
        "prefer_scale_out": blended > float(full.get("net_profit") or 0.0),
    }
