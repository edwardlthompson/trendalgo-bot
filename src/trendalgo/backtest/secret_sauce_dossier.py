"""Heartbeat dossier types for Secret Sauce (operator-local GEN_SECRET)."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from trendalgo.backtest.oracle_pattern_mine import CompositeRule, RuleConjunct

_SECRET_ID = "GEN_SECRET_1"


@dataclass(frozen=True)
class HeartbeatDossier:
    rule: CompositeRule
    exit_rule: CompositeRule
    formula_en: str
    train_coverage: float
    holdout_coverage: float
    swing_hits: tuple[bool, ...]
    exit_hits: tuple[bool, ...]
    oracle_entry_indexes: tuple[int, ...]
    oracle_exit_indexes: tuple[int, ...]
    anti_cheat: str
    # Phase 0 residual instrumentation (additive; consumers use .get / defaults).
    residual_entry_indexes: tuple[int, ...] = ()
    residual_exit_indexes: tuple[int, ...] = ()
    residual_feature_hits: tuple[dict[str, Any], ...] = ()
    oracle_gap_net_pct: float | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "rule": self.rule.to_dict(),
            "exit_rule": self.exit_rule.to_dict(),
            "entry_conjuncts": [asdict(c) for c in self.rule.conjuncts],
            "exit_conjuncts": [asdict(c) for c in self.exit_rule.conjuncts],
            "formula_en": self.formula_en,
            "train_coverage": self.train_coverage,
            "holdout_coverage": self.holdout_coverage,
            "swing_hits": list(self.swing_hits),
            "exit_hits": list(self.exit_hits),
            "oracle_entry_indexes": list(self.oracle_entry_indexes),
            "oracle_exit_indexes": list(self.oracle_exit_indexes),
            "anti_cheat": self.anti_cheat,
            "residual_entry_indexes": list(self.residual_entry_indexes),
            "residual_exit_indexes": list(self.residual_exit_indexes),
            "residual_feature_hits": [dict(x) for x in self.residual_feature_hits],
            "oracle_gap_net_pct": self.oracle_gap_net_pct,
            "requires_backtest": True,
        }

    def eval_params(self) -> dict[str, Any]:
        """Slim params for backtest_one — no dossier dump."""
        return {
            "strategy_id": self.rule.strategy_id,
            "entry_conjuncts": [asdict(c) for c in self.rule.conjuncts],
            "exit_conjuncts": [asdict(c) for c in self.exit_rule.conjuncts],
            "rationale": self.rule.rationale,
        }


def _conjuncts_from(raw: list[Any] | None) -> tuple[RuleConjunct, ...]:
    out: list[RuleConjunct] = []
    for item in raw or []:
        if not isinstance(item, dict):
            continue
        out.append(
            RuleConjunct(
                feature=str(item.get("feature") or ""),
                op=str(item.get("op") or ">="),
                value=float(item.get("value") or 0.0),
            )
        )
    return tuple(out)


def _residual_hits_from(raw: object) -> tuple[dict[str, Any], ...]:
    if not isinstance(raw, list):
        return ()
    out: list[dict[str, Any]] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        feats = item.get("features")
        out.append(
            {
                "side": str(item.get("side") or ""),
                "index": int(item.get("index") or 0),
                "features": [str(x) for x in feats] if isinstance(feats, list) else [],
            }
        )
    return tuple(out)


def dossier_from_dict(raw: dict[str, Any] | None) -> HeartbeatDossier | None:
    if not isinstance(raw, dict):
        return None
    entry = _conjuncts_from(raw.get("entry_conjuncts"))
    exit_c = _conjuncts_from(raw.get("exit_conjuncts"))
    rule_raw = raw.get("rule") if isinstance(raw.get("rule"), dict) else {}
    exit_raw = raw.get("exit_rule") if isinstance(raw.get("exit_rule"), dict) else {}
    if not entry and isinstance(rule_raw, dict):
        entry = _conjuncts_from(rule_raw.get("conjuncts"))
    if not exit_c and isinstance(exit_raw, dict):
        exit_c = _conjuncts_from(exit_raw.get("conjuncts"))
    if not entry:
        return None
    if not exit_c:
        exit_c = entry
    sid = str((rule_raw or {}).get("strategy_id") or _SECRET_ID)
    entry_rule = CompositeRule(
        strategy_id=sid,
        conjuncts=entry,
        rationale=str((rule_raw or {}).get("rationale") or ""),
        requires_backtest=True,
    )
    exit_rule = CompositeRule(
        strategy_id=sid,
        conjuncts=exit_c,
        rationale=str((exit_raw or {}).get("rationale") or "exit"),
        requires_backtest=True,
    )
    gap_raw = raw.get("oracle_gap_net_pct")
    gap: float | None
    try:
        gap = float(gap_raw) if gap_raw is not None else None
    except (TypeError, ValueError):
        gap = None
    return HeartbeatDossier(
        rule=entry_rule,
        exit_rule=exit_rule,
        formula_en=str(raw.get("formula_en") or ""),
        train_coverage=float(raw.get("train_coverage") or 0.0),
        holdout_coverage=float(raw.get("holdout_coverage") or 0.0),
        swing_hits=tuple(bool(x) for x in (raw.get("swing_hits") or [])),
        exit_hits=tuple(bool(x) for x in (raw.get("exit_hits") or [])),
        oracle_entry_indexes=tuple(int(x) for x in (raw.get("oracle_entry_indexes") or [])),
        oracle_exit_indexes=tuple(int(x) for x in (raw.get("oracle_exit_indexes") or [])),
        anti_cheat=str(raw.get("anti_cheat") or ""),
        residual_entry_indexes=tuple(int(x) for x in (raw.get("residual_entry_indexes") or [])),
        residual_exit_indexes=tuple(int(x) for x in (raw.get("residual_exit_indexes") or [])),
        residual_feature_hits=_residual_hits_from(raw.get("residual_feature_hits")),
        oracle_gap_net_pct=gap,
    )


def is_secret_sauce_indicator(indicator: object) -> bool:
    text = str(indicator or "").strip()
    upper = text.upper()
    return text.startswith("Secret Sauce") or upper.startswith("GEN_SECRET")


def formula_english(entry: CompositeRule, exit_rule: CompositeRule) -> str:
    def body(rule: CompositeRule) -> str:
        parts = [f"{c.feature} {c.op} {c.value:.4g}" for c in rule.conjuncts]
        return " AND ".join(parts) if parts else "(none)"

    return f"Enter when {body(entry)}. Exit when {body(exit_rule)}."
