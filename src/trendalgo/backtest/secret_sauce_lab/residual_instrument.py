"""Phase 0 — residual Oracle swings + causal feature hits (instrumentation only)."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from trendalgo.backtest.secret_sauce_lab.columnar import feature_matrix

_TOP_N = 8


def residual_indexes(
    oracle_indexes: list[int] | tuple[int, ...],
    hits: list[bool] | tuple[bool, ...],
) -> tuple[int, ...]:
    """Oracle bar indexes where the recipe did not fire."""
    out: list[int] = []
    for i, idx in enumerate(oracle_indexes):
        hit = bool(hits[i]) if i < len(hits) else False
        if not hit:
            out.append(int(idx))
    return tuple(out)


def true_features_at(
    cols: dict[str, np.ndarray],
    index: int,
    *,
    top_n: int = _TOP_N,
) -> list[str]:
    """Binary/causal fires at ``index`` (value ≈ 1.0), capped at ``top_n``."""
    if index < 0 or not cols:
        return []
    hits: list[str] = []
    for key, arr in cols.items():
        if index >= len(arr):
            continue
        # Binary fires only (crosses / confirms / flags) — not continuous oscillators.
        if abs(float(arr[index]) - 1.0) < 1e-6:
            hits.append(key)
            if len(hits) >= top_n:
                break
    return hits


def residual_feature_hits(
    df: pd.DataFrame,
    *,
    residual_entries: tuple[int, ...],
    residual_exits: tuple[int, ...],
    top_n: int = _TOP_N,
) -> tuple[dict[str, Any], ...]:
    """Per residual bar: side, index, and top-N features true at that bar."""
    if df.empty or (not residual_entries and not residual_exits):
        return ()
    cols, _feats = feature_matrix(df)
    if not cols:
        return ()
    rows: list[dict[str, Any]] = []
    for idx in residual_entries:
        rows.append(
            {
                "side": "entry",
                "index": int(idx),
                "features": true_features_at(cols, int(idx), top_n=top_n),
            }
        )
    for idx in residual_exits:
        rows.append(
            {
                "side": "exit",
                "index": int(idx),
                "features": true_features_at(cols, int(idx), top_n=top_n),
            }
        )
    return tuple(rows)


def build_residual_fields(
    df: pd.DataFrame,
    *,
    entries: list[int],
    exits: list[int],
    swing_hits: tuple[bool, ...],
    exit_hits: tuple[bool, ...],
    sauce_net: float | None = None,
    oracle_net: float | None = None,
) -> dict[str, Any]:
    """Additive dossier payload for residuals + optional Oracle gap."""
    res_e = residual_indexes(entries, swing_hits)
    res_x = residual_indexes(exits, exit_hits)
    gap: float | None = None
    if sauce_net is not None and oracle_net is not None:
        gap = float(oracle_net) - float(sauce_net)
    return {
        "residual_entry_indexes": res_e,
        "residual_exit_indexes": res_x,
        "residual_feature_hits": residual_feature_hits(
            df, residual_entries=res_e, residual_exits=res_x
        ),
        "oracle_gap_net_pct": gap,
    }
