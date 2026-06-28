"""Glossary entries for custom (Fibonacci) indicators."""

from __future__ import annotations

from trendalgo.ta.extended_catalog import CUSTOM_TA_NAMES


def _e(title: str, short: str, long: str, formula: str) -> dict[str, str]:
    return {"title": title, "short": short, "long": long, "formula": formula}


EXTENDED_GLOSSARY_ENTRIES: dict[str, dict[str, str]] = {
    "FIB_RETRACE": _e(
        "Fibonacci Retracement Levels",
        "Horizontal support/resistance from swing high–low using 23.6%–78.6% ratios.",
        "Fibonacci retracement plots proportional pullback levels between a recent swing high and swing low. "
        "Traders watch 38.2%, 50%, and 61.8% as common reaction zones during trends.",
        "Level(p) = SwingHigh − p × (SwingHigh − SwingLow); p ∈ {0.236, 0.382, 0.5, 0.618, 0.786}",
    ),
    "FIB_EXT": _e(
        "Fibonacci Extension Levels",
        "Projected targets beyond the swing using 127.2%, 161.8%, and 261.8% ratios.",
        "Fibonacci extensions estimate where price may reach after breaking a swing. "
        "They are used for profit targets and breakout continuation zones.",
        "Ext(p) = SwingHigh + p × (SwingHigh − SwingLow); p ∈ {0.272, 0.618, 1.618}",
    ),
}

if set(EXTENDED_GLOSSARY_ENTRIES) != set(CUSTOM_TA_NAMES):
    missing = sorted(set(CUSTOM_TA_NAMES) - set(EXTENDED_GLOSSARY_ENTRIES))
    extra = sorted(set(EXTENDED_GLOSSARY_ENTRIES) - set(CUSTOM_TA_NAMES))
    raise ValueError(f"EXTENDED_GLOSSARY mismatch: missing={missing}, extra={extra}")
