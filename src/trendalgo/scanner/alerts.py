"""LTS alerting tiers merged into TrendAlgo (O9, NT2)."""

from __future__ import annotations

from trendalgo.scanner.snapshot import QualifiedSnapshot
from trendalgo.scanner.store import ScannerStore


def tier_for_opportunity(uniformity: float, gain_pct: float) -> str:
    if uniformity >= 0.7 and gain_pct >= 0.05:
        return "A"
    if uniformity >= 0.6 or gain_pct >= 0.03:
        return "B"
    return "C"


def emit_alerts_for_snapshot(store: ScannerStore, snapshot: QualifiedSnapshot) -> None:
    for opp in snapshot.opportunities[:5]:
        tier = tier_for_opportunity(opp.uniformity, opp.gain_pct)
        if tier == "C":
            continue
        store.log_alert(
            tier,
            opp.pair,
            f"{opp.pair} uniformity={opp.uniformity:.2f} gain={opp.gain_pct*100:.1f}%",
        )
