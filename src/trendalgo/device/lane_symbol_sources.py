"""Build Backtest/Scanner symbol choices from all desk universes."""

from __future__ import annotations

from pathlib import Path

from trendalgo.brokers.forex_universe import load_forex_universe
from trendalgo.brokers.tradfi_universe import load_tradfi_universe
from trendalgo.device.lane_prefs import LanePrefs
from trendalgo.exchanges.static_kraken_usd import KRAKEN_USD_PAIRS


def research_symbol_choices(
    root: Path | None = None,
    *,
    prefs: LanePrefs | None = None,
) -> tuple[str, ...]:
    """All desk universes (Crypto + TradFi + Forex). Prefs kept for call-site compat."""
    _ = root, prefs  # desks are always available; Auto-scan does not hide symbols
    out: list[str] = []
    seen: set[str] = set()
    for pair in KRAKEN_USD_PAIRS:
        if pair not in seen:
            seen.add(pair)
            out.append(pair)
    for sym in load_tradfi_universe(root=root):
        if sym not in seen:
            seen.add(sym)
            out.append(sym)
    for pair in load_forex_universe():
        if pair not in seen:
            seen.add(pair)
            out.append(pair)
    return tuple(out)
