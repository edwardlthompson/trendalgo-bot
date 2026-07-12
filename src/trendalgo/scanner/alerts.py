"""LTS alerting tiers merged into TrendAlgo (O9, NT2)."""

from __future__ import annotations

from collections.abc import Callable

from trendalgo.alerts.market_events import evaluate_market_event
from trendalgo.scanner.snapshot import QualifiedSnapshot
from trendalgo.scanner.store import ScannerStore

AlertSink = Callable[[str, str, str], object]


def tier_for_opportunity(uniformity: float, gain_pct: float) -> str:
    if uniformity >= 0.7 and gain_pct >= 0.05:
        return "A"
    if uniformity >= 0.6 or gain_pct >= 0.03:
        return "B"
    return "C"


def emit_alerts_for_snapshot(
    store: ScannerStore,
    snapshot: QualifiedSnapshot,
    on_alert: AlertSink | None = None,
) -> None:
    for opp in snapshot.opportunities[:5]:
        tier = tier_for_opportunity(opp.uniformity, opp.gain_pct)
        message = f"{opp.pair} uniformity={opp.uniformity:.2f} gain={opp.gain_pct * 100:.1f}%"
        store.log_alert(
            tier,
            opp.pair,
            message,
        )
        if on_alert:
            on_alert("scanner", f"Tier {tier} scanner alert", message)
        event = evaluate_market_event(opp.pair, opp.gain_pct, opp.volume_score)
        if event and on_alert:
            event_type = str(event["type"]).replace("_", " ").title()
            on_alert("market", event_type, str(event["message"]))
