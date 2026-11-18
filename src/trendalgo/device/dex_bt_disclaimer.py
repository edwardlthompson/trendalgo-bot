"""Device-facing DEX backtest honesty copy (DEX-P3a)."""

from __future__ import annotations

from trendalgo.backtest.dex_proxy_bt import DEX_PROXY_BT_DISCLAIMER
from trendalgo.device import strings as S


def dex_backtest_disclaimer() -> str:
    """Prefer i18n string; fall back to shared backtest constant."""
    text = getattr(S, "DEX_BT_DISCLAIMER", "") or ""
    return str(text).strip() or DEX_PROXY_BT_DISCLAIMER
