"""Mine one global causal Secret Sauce entry+exit rule (delegates to Lab)."""

from __future__ import annotations

from typing import Any

import pandas as pd

from trendalgo.backtest.secret_sauce_dossier import (
    HeartbeatDossier,
    dossier_from_dict,
    is_secret_sauce_indicator,
)
from trendalgo.backtest.secret_sauce_features import entries_for_secret_sauce
from trendalgo.backtest.secret_sauce_search import default_search_fee

_SECRET_ID = "GEN_SECRET_1"
_STAKE = 1000.0

__all__ = [
    "HeartbeatDossier",
    "dossier_from_dict",
    "entries_for_secret_sauce",
    "is_secret_sauce_indicator",
    "mine_secret_sauce",
]


def mine_secret_sauce(
    df: pd.DataFrame,
    *,
    oracle_trades: list[dict[str, Any]],
    strategy_id: str = _SECRET_ID,
    fee: Any | None = None,
    stake_usd: float = _STAKE,
) -> HeartbeatDossier | None:
    """Fit entry+exit via Secret Sauce Lab (regime budgets + fee-aware P&L)."""
    from trendalgo.backtest.secret_sauce_lab import run_secret_sauce_lab

    if df.empty or len(oracle_trades) < 2:
        return None
    use_fee = fee if fee is not None else default_search_fee()
    try:
        packed = run_secret_sauce_lab(
            df,
            fee=use_fee,
            stake_usd=stake_usd,
            oracle_trades=oracle_trades,
            strategy_id=strategy_id,
        )
    except (TypeError, ValueError, KeyError, IndexError):
        return None
    if packed is None:
        return None
    dossier, _regime = packed
    return dossier
