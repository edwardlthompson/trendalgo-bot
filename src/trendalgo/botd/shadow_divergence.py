"""Shadow divergence classifier (row 21; E5, L1).

Compares the engine's run on recorded candles with the host's shadow run. Each mismatch gets one
class, so none is hidden:

- data: a bar is missing, repeated, or out of order in the shadow feed; a trade overlaps a missing
  bar; or an exit reason is not one the port emits
- signal: one side enters or exits and the other does not, or a signal exit lands on another bar
- stop: a take profit or trailing stop differs in reason or exit hour (L1), or a stop exit fills at
  another price
- fill: the entry, the quantity, or a signal exit fills outside the tolerance (E5)

Bar and trade times are text in one format, so text order is time order.
"""

from __future__ import annotations

import math
from bisect import bisect_left
from collections.abc import Sequence

from trendalgo.botd.shadow_report import Divergence, Kind
from trendalgo.lts_vendor.backtesting.models import Trade

STOP_REASONS = frozenset({"take_profit", "trailing_take_profit", "trailing_stop_loss"})
KNOWN_REASONS = STOP_REASONS | {"sell_signal"}


def classify_run(
    expected_bars: Sequence[str],
    observed_bars: Sequence[str],
    expected_trades: Sequence[Trade],
    observed_trades: Sequence[Trade],
    *,
    price_bps: float,
) -> list[Divergence]:
    """Every divergence, each with one class. `price_bps` is the price and quantity tolerance in
    basis points of the engine's value. It has no default: the owner sets it."""
    if not price_bps >= 0:  # also refuses NaN
        raise ValueError("price_bps must be zero or more")
    missing = sorted(set(expected_bars) - set(observed_bars))
    found = [Divergence("data", bar, "bar missing from the shadow feed") for bar in missing]
    found += _feed_problems(observed_bars)
    engine, engine_dupes = _by_entry(expected_trades, "engine")
    shadow, shadow_dupes = _by_entry(observed_trades, "shadow")
    found += engine_dupes + shadow_dupes
    for entry in sorted(engine.keys() | shadow.keys()):
        found += _entry_divergences(entry, engine.get(entry), shadow.get(entry), missing, price_bps)
    return found


def _feed_problems(bars: Sequence[str]) -> list[Divergence]:
    problems: list[Divergence] = []
    seen: set[str] = set()
    latest = ""
    for bar in bars:
        if bar in seen:
            problems.append(Divergence("data", bar, "bar repeated in the shadow feed"))
            continue
        if bar < latest:
            problems.append(Divergence("data", bar, "bar out of order in the shadow feed"))
        seen.add(bar)
        latest = max(latest, bar)
    return problems


def _by_entry(trades: Sequence[Trade], label: str) -> tuple[dict[str, Trade], list[Divergence]]:
    by_entry: dict[str, Trade] = {}
    extra: list[Divergence] = []
    for trade in trades:
        if trade.entry_time in by_entry:
            detail = f"the {label} run has two trades on this entry bar"
            extra.append(Divergence("data", trade.entry_time, detail))
        else:
            by_entry[trade.entry_time] = trade
    return by_entry, extra


def _entry_divergences(
    entry: str,
    engine_trade: Trade | None,
    shadow_trade: Trade | None,
    missing: list[str],
    price_bps: float,
) -> list[Divergence]:
    if engine_trade is not None and shadow_trade is not None:
        return _pair_divergences(engine_trade, shadow_trade, missing=missing, price_bps=price_bps)
    trade = engine_trade if engine_trade is not None else shadow_trade
    if trade is None:
        return []
    kind: Kind = "data" if _overlaps_gap(trade, missing) else "signal"
    who = "shadow" if engine_trade is not None else "engine"
    return [Divergence(kind, entry, f"the {who} run has no entry on this bar")]


def _pair_divergences(
    engine: Trade, shadow: Trade, *, missing: list[str], price_bps: float
) -> list[Divergence]:
    found = [
        Divergence(kind, engine.entry_time, detail)
        for kind, detail in _pair_mismatches(engine, shadow, price_bps)
    ]
    if found and (_overlaps_gap(engine, missing) or _overlaps_gap(shadow, missing)):
        detail = "trade overlaps a bar missing from the shadow feed"
        return [Divergence("data", engine.entry_time, detail)]
    return found


def _pair_mismatches(engine: Trade, shadow: Trade, price_bps: float) -> list[tuple[Kind, str]]:
    if engine.exit_reason not in KNOWN_REASONS or shadow.exit_reason not in KNOWN_REASONS:
        return [("data", "an exit reason is not one the port emits")]
    if engine.exit_reason != shadow.exit_reason:
        stop = STOP_REASONS & {engine.exit_reason, shadow.exit_reason}
        kind: Kind = "stop" if stop else "signal"
        return [(kind, f"exit {engine.exit_reason} against {shadow.exit_reason}")]
    stop_exit = engine.exit_reason in STOP_REASONS
    if engine.exit_time != shadow.exit_time:
        return [
            (
                "stop" if stop_exit else "signal",
                f"exit at {engine.exit_time} against {shadow.exit_time}",
            )
        ]
    found: list[tuple[Kind, str]] = []
    if _gap_bps(engine.entry_price, shadow.entry_price) > price_bps:
        found.append(("fill", f"entry price {engine.entry_price} against {shadow.entry_price}"))
    if _gap_bps(engine.quantity, shadow.quantity) > price_bps:
        found.append(("fill", f"quantity {engine.quantity} against {shadow.quantity}"))
    if _gap_bps(engine.exit_price, shadow.exit_price) > price_bps:
        kind = "stop" if stop_exit else "fill"
        found.append((kind, f"exit price {engine.exit_price} against {shadow.exit_price}"))
    return found


def _overlaps_gap(trade: Trade, missing: list[str]) -> bool:
    index = bisect_left(missing, trade.entry_time)
    return index < len(missing) and missing[index] <= trade.exit_time


def _gap_bps(expected: float, observed: float) -> float:
    """Size of the gap in basis points of the expected value. A NaN or a zero base never passes."""
    difference = abs(observed - expected)
    if not math.isfinite(difference):
        return math.inf
    if difference == 0:
        return 0.0
    if expected == 0:
        return math.inf
    return difference / abs(expected) * 10_000.0
