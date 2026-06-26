"""AI backtest summary — rule-based VPS default; Ollama optional (T12, AI1)."""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any

from trendalgo.schemas.backtest_result import BacktestResult


def rule_based_summary(result: BacktestResult) -> str:
    wins = sum(1 for t in result.trades if t.profit_abs > 0)
    losses = len(result.trades) - wins
    dd = result.max_drawdown or 0.0
    tone = "favorable" if result.profit_total > 0 and dd < 0.1 else "cautious"
    return (
        f"{result.strategy} on {result.pair}: {result.total_trades} trades, "
        f"net ${result.profit_total:.2f} ({result.profit_total_pct * 100:.1f}%). "
        f"Win/loss {wins}/{losses}, max drawdown {dd * 100:.1f}%. "
        f"Assessment: {tone} — verify on longer timerange before live."
    )


OLLAMA_PROMPT = """Summarize this backtest in 3 bullet points. No trade advice.
Data: {json}
"""


def ollama_summary(result: BacktestResult, *, host: str | None = None) -> str | None:
    base = host or os.environ.get("OLLAMA_HOST", "http://127.0.0.1:11434")
    payload = {
        "model": os.environ.get("OLLAMA_MODEL", "llama3.2"),
        "prompt": OLLAMA_PROMPT.format(json=json.dumps(result.model_dump(mode="json"))),
        "stream": False,
    }
    try:
        req = urllib.request.Request(
            f"{base.rstrip('/')}/api/generate",
            data=json.dumps(payload).encode(),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            body: dict[str, Any] = json.loads(resp.read().decode())
            return str(body.get("response", "")).strip() or None
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, KeyError):
        return None


def analyze_backtest(result: BacktestResult) -> dict[str, str]:
    summary = rule_based_summary(result)
    ai = ollama_summary(result)
    return {
        "summary": summary,
        "engine": "ollama" if ai else "rule-based",
        "detail": ai or summary,
    }
