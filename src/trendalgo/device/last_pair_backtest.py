"""Persist the last Backtest-tab All-TA result so it survives app restarts."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from trendalgo.device.profile import read_json, write_json

LAST_BACKTEST_FILE = "last_pair_backtest.json"


def has_tradable_results(rows: list[dict[str, Any]]) -> bool:
    """True when at least one row is a real result (not a skip placeholder)."""
    return any(not str(row.get("skip_reason") or "").strip() for row in rows)


def save_last_pair_backtest(
    root: Path,
    pair: str,
    rows: list[dict[str, Any]],
    *,
    market_context: dict[str, Any] | None = None,
) -> None:
    text = str(pair or "").strip().upper()
    if not text or "/" not in text or not rows or not has_tradable_results(rows):
        return
    payload: dict[str, Any] = {"pair": text, "rows": list(rows)}
    if isinstance(market_context, dict):
        payload["market_context"] = market_context
    write_json(root / LAST_BACKTEST_FILE, payload)


def load_last_pair_backtest(
    root: Path,
) -> tuple[str, list[dict[str, Any]], dict[str, Any] | None] | None:
    data = read_json(root / LAST_BACKTEST_FILE)
    if not isinstance(data, dict):
        return None
    pair = str(data.get("pair") or "").strip().upper()
    rows = data.get("rows")
    if not pair or "/" not in pair or not isinstance(rows, list) or not rows:
        return None
    out = [row for row in rows if isinstance(row, dict)]
    if not out or not has_tradable_results(out):
        return None
    ctx = data.get("market_context")
    market_context = ctx if isinstance(ctx, dict) else None
    return pair, out, market_context
