"""Fixed lookback for All-TA / pair scans — always 30 days (apples-to-apples)."""

from __future__ import annotations

# Every strategy × TF comparison uses the same calendar window.
SCAN_LOOKBACK_DAYS = 30


def days_for_timeframe(_timeframe: str = "", *, min_bars: int | None = None) -> int:
    """Return the fixed scan lookback (ignores TF — slow TFs may simply lack bars)."""
    del min_bars  # kept for call-site compatibility
    return SCAN_LOOKBACK_DAYS
