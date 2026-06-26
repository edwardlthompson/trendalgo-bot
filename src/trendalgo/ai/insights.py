"""Expanded AI strategy insights with disclaimer (AI1)."""

from __future__ import annotations

from typing import Any

from trendalgo.ai.backtest_summary import analyze_backtest, rule_based_summary
from trendalgo.schemas.backtest_result import BacktestResult


DISCLAIMER = (
    "Insights are rule-based on VPS by default. Not financial advice. "
    "Ollama summaries are dev-only unless OLLAMA_HOST is set."
)


def expanded_insights(result: BacktestResult, attribution: dict[str, Any] | None = None) -> dict[str, str]:
    base = analyze_backtest(result)
    summary = rule_based_summary(result)
    attr_note = ""
    if attribution:
        attr_note = (
            f" Signal attribution: LTS ${attribution.get('lts_contribution_usd', 0):.2f}, "
            f"scanner ${attribution.get('scanner_contribution_usd', 0):.2f}."
        )
    return {
        **base,
        "disclaimer": DISCLAIMER,
        "detail": base["detail"] + attr_note,
        "summary": summary + attr_note,
    }
