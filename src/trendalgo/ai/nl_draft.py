"""Natural-language strategy draft — rule-based VPS; user confirms (AI8)."""

from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request
from typing import Any


def rule_based_draft(text: str) -> dict[str, Any]:
    lower = text.lower()
    params: dict[str, Any] = {"rsi_entry": 35, "rsi_exit": 65, "lts_uniform_min": 0.55}
    strategy_id = "multi-tf-example"
    notes: list[str] = []

    if "dca" in lower or "accumulate" in lower:
        strategy_id = "smart-dca"
        params = {"interval_hours": 24, "dip_boost_pct": 0.02}
        notes.append("Detected DCA intent")
    if "grid" in lower:
        strategy_id = "grid-trading"
        params = {"grid_levels": 5, "grid_spacing_pct": 0.02}
        notes.append("Detected grid intent")
    if "scanner" in lower or "uptrend" in lower or "lts" in lower:
        strategy_id = "strong-uptrend-scanner"
        params["lts_uniform_min"] = 0.6
        notes.append("Detected scanner/LTS intent")

    rsi_match = re.search(r"rsi\s*(?:entry|buy)?\s*(\d+)", lower)
    if rsi_match:
        params["rsi_entry"] = int(rsi_match.group(1))
        notes.append(f"RSI entry {params['rsi_entry']}")

    return {
        "strategy_id": strategy_id,
        "params": params,
        "engine": "rule-based",
        "notes": notes,
        "requires_user_confirmation": True,
        "disclaimer": "Draft only — not financial advice. Backtest before live.",
    }


def ollama_draft(text: str) -> dict[str, Any] | None:
    host = os.environ.get("OLLAMA_HOST")
    if not host:
        return None
    prompt = (
        "Extract trading strategy params as JSON with strategy_id and params keys only. "
        f"User text: {text}"
    )
    payload = {
        "model": os.environ.get("OLLAMA_MODEL", "llama3.2"),
        "prompt": prompt,
        "stream": False,
    }
    try:
        req = urllib.request.Request(
            f"{host.rstrip('/')}/api/generate",
            data=json.dumps(payload).encode(),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            body = json.loads(resp.read().decode())
            raw = str(body.get("response", ""))
            return {"engine": "ollama", "raw": raw, "requires_user_confirmation": True}
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError):
        return None


def draft_from_nl(text: str) -> dict[str, Any]:
    ai = ollama_draft(text)
    if ai:
        base = rule_based_draft(text)
        return {**base, **ai}
    return rule_based_draft(text)
