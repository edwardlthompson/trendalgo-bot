"""Mine composite entry rules from oracle swings vs actual strategy trades."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class RuleConjunct:
    feature: str
    op: str  # >= or <=
    value: float


@dataclass(frozen=True)
class CompositeRule:
    strategy_id: str
    conjuncts: tuple[RuleConjunct, ...]
    rationale: str
    requires_backtest: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "strategy_id": self.strategy_id,
            "conjuncts": [asdict(c) for c in self.conjuncts],
            "rationale": self.rationale,
            "requires_backtest": self.requires_backtest,
        }

    def summary(self) -> str:
        parts = [f"{c.feature} {c.op} {c.value:.4g}" for c in self.conjuncts]
        body = " AND ".join(parts) if parts else "(no conjuncts)"
        return f"{self.strategy_id}: enter when {body}. {self.rationale}"


def mine_oracle_rule(
    df: pd.DataFrame,
    *,
    oracle_trades: list[dict[str, Any]],
    strategy_trades: list[dict[str, Any]] | None = None,
    strategy_id: str = "GEN_ORACLE_1",
) -> CompositeRule | None:
    """Build a simple threshold rule from features at missed oracle entries."""
    if df.empty or not oracle_trades:
        return None
    features = _bar_features(df)
    missed = _missed_entries(oracle_trades, strategy_trades or [])
    if not missed:
        missed = [int(t.get("entry_index") or 0) for t in oracle_trades]
    samples = [features[i] for i in missed if 0 <= i < len(features)]
    if len(samples) < 2:
        return None
    conjuncts = _threshold_conjuncts(samples, features)
    if not conjuncts:
        return None
    rationale = (
        f"Mined from {len(missed)} oracle entry bar(s) where strategies lagged or missed "
        f"perfect trough→peak swings (operator-local; requires_backtest)."
    )
    return CompositeRule(
        strategy_id=strategy_id,
        conjuncts=tuple(conjuncts),
        rationale=rationale,
    )


def entries_for_rule(df: pd.DataFrame, rule: CompositeRule) -> np.ndarray:
    """Boolean entry mask for a composite rule (exit = next bar after entry for scan)."""
    feats = _bar_features(df)
    n = len(df)
    entries = np.zeros(n, dtype=bool)
    for i, feat in enumerate(feats):
        if _match(feat, rule.conjuncts):
            entries[i] = True
    return entries


def _missed_entries(
    oracle: list[dict[str, Any]],
    actual: list[dict[str, Any]],
) -> list[int]:
    actual_idx = {int(t.get("entry_index") or -1) for t in actual}
    missed: list[int] = []
    for trade in oracle:
        idx = int(trade.get("entry_index") or -1)
        if idx < 0:
            continue
        if idx not in actual_idx and not any(abs(idx - a) <= 2 for a in actual_idx if a >= 0):
            missed.append(idx)
    return missed


def _bar_features(df: pd.DataFrame) -> list[dict[str, float]]:
    closes = df["close"].to_numpy(dtype=float)
    highs = df["high"].to_numpy(dtype=float) if "high" in df.columns else closes
    lows = df["low"].to_numpy(dtype=float) if "low" in df.columns else closes
    vols = df["volume"].to_numpy(dtype=float) if "volume" in df.columns else np.ones(len(df))
    out: list[dict[str, float]] = []
    for i in range(len(df)):
        prev = closes[i - 1] if i else closes[i]
        ret = (closes[i] / prev - 1.0) if prev else 0.0
        rng = ((highs[i] - lows[i]) / closes[i]) if closes[i] else 0.0
        vol_ma = float(np.mean(vols[max(0, i - 5) : i + 1]))
        vol_ratio = float(vols[i] / vol_ma) if vol_ma else 1.0
        out.append({"ret_1": ret, "range_pct": rng, "vol_ratio": vol_ratio})
    return out


def _threshold_conjuncts(
    samples: list[dict[str, float]],
    all_feats: list[dict[str, float]],
) -> list[RuleConjunct]:
    """Prefer features where sample median sits above/below global median."""
    keys = ("ret_1", "range_pct", "vol_ratio")
    conj: list[RuleConjunct] = []
    for key in keys:
        sample_vals = [s[key] for s in samples]
        global_vals = [f[key] for f in all_feats]
        s_med = float(np.median(sample_vals))
        g_med = float(np.median(global_vals))
        if abs(s_med - g_med) < 1e-9:
            continue
        if s_med >= g_med:
            conj.append(RuleConjunct(feature=key, op=">=", value=round(s_med, 6)))
        else:
            conj.append(RuleConjunct(feature=key, op="<=", value=round(s_med, 6)))
        if len(conj) >= 2:
            break
    return conj


def _match(feat: dict[str, float], conjuncts: tuple[RuleConjunct, ...]) -> bool:
    for c in conjuncts:
        val = float(feat.get(c.feature) or 0.0)
        if c.op == ">=" and not (val >= c.value):
            return False
        if c.op == "<=" and not (val <= c.value):
            return False
    return bool(conjuncts)
