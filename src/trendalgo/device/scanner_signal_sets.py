"""Scanner backtest signal sets: 3Commas (LTS 12) vs All TA (fleet catalog)."""

from __future__ import annotations

BT_SET_3COMMAS = "3commas"
BT_SET_ALL_TA = "all_ta"

# Display labels match LTS SIGNAL_REGISTRY keys (3Commas-equivalent set).
THREE_COMMAS_INDICATORS: tuple[str, ...] = (
    "RSI",
    "Stochastic",
    "MACD",
    "EMA Crossover",
    "SMA Crossover",
    "Bollinger %B",
    "CCI",
    "Ultimate Oscillator",
    "MFI",
    "ADX",
    "Parabolic SAR",
    "Heikin Ashi",
)

# Catalog / fleet strategy_ids that correspond to the 3Commas set (for Results *).
THREE_COMMAS_CATALOG_IDS: frozenset[str] = frozenset(
    {
        "RSI",
        "STOCH",
        "MACD",
        "EMA",
        "SMA",
        "BBANDS",
        "CCI",
        "ULTOSC",
        "MFI",
        "ADX",
        "SAR",
        "PSAR",
    }
)

_BT_SETS = frozenset({BT_SET_3COMMAS, BT_SET_ALL_TA})


def normalize_bt_signal_set(raw: object) -> str:
    """Return a known set id; unknown/empty → 3Commas (default)."""
    text = str(raw or "").strip().lower().replace("-", "_").replace(" ", "_")
    if text in {"all", "all_ta", "allta", "ta"}:
        return BT_SET_ALL_TA
    if text in _BT_SETS:
        return text
    return BT_SET_3COMMAS


def is_three_commas_indicator(name: str) -> bool:
    """True when name matches a 3Commas LTS label or catalog id (case-insensitive)."""
    key = str(name or "").strip()
    if not key:
        return False
    upper = key.upper()
    if upper in THREE_COMMAS_CATALOG_IDS:
        return True
    return any(key.casefold() == label.casefold() for label in THREE_COMMAS_INDICATORS)
