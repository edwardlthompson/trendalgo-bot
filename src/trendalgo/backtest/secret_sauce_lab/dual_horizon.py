"""G — dual-horizon: entry seeds on dense TF, remap exits/arming from Oracle TF."""

from __future__ import annotations

from typing import Any

from trendalgo.backtest.secret_sauce_lab.helper_pack import pack_helper_row
from trendalgo.backtest.secret_sauce_lab.multi_tf_lab import remap_oracle_trades
from trendalgo.backtest.secret_sauce_lab.run import run_secret_sauce_lab
from trendalgo.exchanges.fees import ExchangeFeeSchedule

_DENSE = ("1h", "2h", "3h", "4h")


def cook_dual_horizon(
    frames_by_tf: dict[str, Any],
    *,
    oracle_tf: str,
    oracle_trades: list[dict[str, Any]],
    fee: ExchangeFeeSchedule,
    stake: float,
    symbol: str,
) -> dict[str, Any] | None:
    """Mine on densest available TF using remapped Oracle swings."""
    primary_tf = next((t for t in _DENSE if frames_by_tf.get(t) is not None), oracle_tf)
    frame = frames_by_tf.get(primary_tf)
    if frame is None or getattr(frame, "empty", True):
        return None
    trades = remap_oracle_trades(frame, oracle_trades, oracle_tf=oracle_tf, search_tf=primary_tf)
    packed = run_secret_sauce_lab(
        frame, fee=fee, stake_usd=stake, oracle_trades=trades, time_budget_s=None
    )
    if packed is None:
        return None
    dossier, regime = packed
    from trendalgo.device.sauce_names import SAUCE_LAB

    # Dual-horizon is an enhancement path for Core; pack as meta note on a Lab-like row
    # Callers may merge into Exit/Armed — here return a packed trial for optional use.
    return pack_helper_row(
        dossier,
        regime,
        frame,
        fee=fee,
        stake=stake,
        symbol=symbol,
        timeframe=primary_tf,
        indicator=SAUCE_LAB,
        extra={"dual_horizon": True, "oracle_tf": oracle_tf, "entry_tf": primary_tf},
    )
