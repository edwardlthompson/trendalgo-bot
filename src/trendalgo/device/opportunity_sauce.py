"""Opportunity Secret Sauce budget: top-N by Oracle + first-join once."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from trendalgo.device.pair_strategy_secret_sauce import best_oracle_row
from trendalgo.device.profile import read_json, write_json

# Sauce Lab / helpers only for this many coins after catalog+deepen for all,
# plus any coin that has never been sauced (first join).
OPPORTUNITY_SAUCE_TOP_N = 10
SAUCE_EVER_FILE = "sauce_ever_symbols.json"

__all__ = [
    "OPPORTUNITY_SAUCE_TOP_N",
    "SAUCE_EVER_FILE",
    "load_sauce_ever",
    "mark_sauce_ever",
    "oracle_rank_score",
    "select_sauce_symbols",
    "select_sauce_symbols_with_first_join",
]


def oracle_rank_score(rows: list[dict[str, Any]]) -> float:
    """Higher is better. Prefer Oracle max net_pct; else best tradable catalog net."""
    oracle = best_oracle_row(rows)
    if oracle is not None:
        try:
            return float(oracle.get("net_pct") or float("-inf"))
        except (TypeError, ValueError):
            pass
    best = float("-inf")
    for row in rows:
        name = str(row.get("indicator") or "")
        if name in {"B&H", "Oracle max"} or name.startswith("Secret Sauce"):
            continue
        if str(row.get("skip_reason") or "").strip():
            continue
        try:
            net = float(row.get("net_pct") or float("-inf"))
        except (TypeError, ValueError):
            continue
        if net > best:
            best = net
    return best


def select_sauce_symbols(
    scored: list[tuple[str, float]],
    *,
    top_n: int = OPPORTUNITY_SAUCE_TOP_N,
) -> list[str]:
    """Return up to ``top_n`` symbols ordered by score descending (stable on ties)."""
    n = max(0, int(top_n))
    ranked = sorted(scored, key=lambda item: (-item[1], item[0]))
    return [sym for sym, _score in ranked[:n] if sym]


def select_sauce_symbols_with_first_join(
    scored: list[tuple[str, float]],
    *,
    ever: set[str],
    top_n: int = OPPORTUNITY_SAUCE_TOP_N,
) -> list[str]:
    """Top-N by Oracle, plus any scored symbol not yet in ``ever`` (first Sauce)."""
    top = select_sauce_symbols(scored, top_n=top_n)
    seen = set(top)
    out = list(top)
    for sym, _score in scored:
        key = str(sym or "").strip().upper()
        if not key or key in seen or key in ever:
            continue
        out.append(key)
        seen.add(key)
    return out


def load_sauce_ever(root: Path) -> set[str]:
    data = read_json(root / SAUCE_EVER_FILE)
    if not isinstance(data, dict):
        return set()
    raw = data.get("symbols")
    if not isinstance(raw, list):
        return set()
    return {str(s).strip().upper() for s in raw if str(s).strip()}


def mark_sauce_ever(root: Path, symbols: list[str] | set[str]) -> set[str]:
    """Union ``symbols`` into persisted sauce-ever set; return the new set."""
    ever = load_sauce_ever(root)
    for sym in symbols:
        key = str(sym or "").strip().upper()
        if key:
            ever.add(key)
    write_json(root / SAUCE_EVER_FILE, {"symbols": sorted(ever)})
    return ever
