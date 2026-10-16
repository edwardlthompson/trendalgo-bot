"""Tradeable strategy pool vs chart/math/reference pools.

TA-Lib ships many *functions* that are not entry/exit strategies on their own:
vector math (ADD), price transforms (TYPPRICE), volatility *measures* (ATR),
and statistics (BETA). Those stay in the full library / glossary by category
but are excluded from All-TA backtests.
"""

from __future__ import annotations

from trendalgo.ta.catalog import all_ta_names
from trendalgo.ta.categories import ta_category
from trendalgo.ta.signal_kinds import MATH_SKIP_IDS, signal_kind

# Categories that are charting / building blocks, not standalone trade systems.
REFERENCE_CATEGORIES: frozenset[str] = frozenset(
    {
        "Math Operators",
        "Math Transform",
        "Statistic Functions",
        "Price Transform",
        "Volatility Indicators",  # ATR/NATR/TRANGE — stops/filters, not entries
        "Cycle Indicators",  # Hilbert diagnostics
    }
)

# Extra IDs to keep out of the trade pool even if category looks tradable.
# Components of DMI (DM) and always-positive ratios belong in reference use.
REFERENCE_EXTRA_IDS: frozenset[str] = frozenset(
    {
        "PLUS_DM",
        "MINUS_DM",
        "ROCR",
        "ROCR100",
        "MA",  # generic MA alias — strategies use SMA/EMA/…
        *MATH_SKIP_IDS,
    }
)

# Categories that remain in the All-TA trade pool (when not in REFERENCE_EXTRA).
TRADE_CATEGORIES: frozenset[str] = frozenset(
    {
        "Overlap Studies",
        "Momentum Indicators",
        "Volume Indicators",
        "Pattern Recognition",
        "Fibonacci & Levels",
        "Extended Indicators",
    }
)


def is_reference_function(strategy_id: str) -> bool:
    """True when the name is a chart/math/helper — not a tradeable strategy."""
    upper = strategy_id.upper()
    if upper in REFERENCE_EXTRA_IDS:
        return True
    if signal_kind(upper) == "math_skip":
        return True
    category = ta_category(upper)
    return category in REFERENCE_CATEGORIES


def is_trade_strategy(strategy_id: str) -> bool:
    """True when All-TA / fleet backtests should evaluate this id."""
    upper = strategy_id.upper()
    if is_reference_function(upper):
        return False
    category = ta_category(upper)
    if category in TRADE_CATEGORIES:
        return True
    # pandas-ta misc that survived category mapping as Extended — allow if not math_skip
    return signal_kind(upper) != "math_skip"


def trade_strategy_names() -> tuple[str, ...]:
    """Names used by Scanner/Backtest All-TA (excludes chart/math pools)."""
    return tuple(name for name in all_ta_names() if is_trade_strategy(name))


def reference_pool_names() -> tuple[str, ...]:
    """Chart analysis / math / stats — still in glossary & library, not All-TA."""
    return tuple(name for name in all_ta_names() if is_reference_function(name))


def pool_label(strategy_id: str) -> str:
    """Short pool name for UI (Trade / Chart & math)."""
    return "Chart & math" if is_reference_function(strategy_id) else "Trade strategy"
