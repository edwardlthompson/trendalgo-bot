"""Derive Secret Sauce / Oracle preference for Avalonia (AV-G-BOT4)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

__all__ = ["derive_oracle_rule"]


def derive_oracle_rule(root: Path, *, pair: str, lane: str = "crypto") -> dict[str, Any]:
    """Prefer Final/Lab sauce row; else report empty so shell can show BACKTEST_DERIVE_EMPTY."""
    from trendalgo.device import strings as S
    from trendalgo.device.sauce_names import create_bot_sauce_preference
    from trendalgo.results_store.desk_surfaces import find_coin, strategy_sheet_from_coin

    pair_u = str(pair or "").strip().upper() or "BTC/USD"
    coin = find_coin(root, pair_u, lane=lane) or {"pair": pair_u}
    rows = strategy_sheet_from_coin(coin)
    sauce = create_bot_sauce_preference(list(rows))
    if sauce is None:
        return {
            "ok": False,
            "error": "empty",
            "pair": pair_u,
            "title": S.BACKTEST_DERIVE_RULE,
            "message": S.BACKTEST_DERIVE_EMPTY,
        }
    dossier = sauce.get("heartbeat_dossier")
    if not isinstance(dossier, dict):
        dossier = {}
    indicator = str(sauce.get("indicator") or "GEN_ORACLE_1")
    return {
        "ok": True,
        "pair": pair_u,
        "indicator": indicator,
        "net_pct": sauce.get("net_pct"),
        "timeframe": sauce.get("timeframe") or "1h",
        "dossier": dossier,
        "prefill": {
            "name": indicator[:40],
            "pair": pair_u,
            "strategy": indicator,
            "timeframe": str(sauce.get("timeframe") or "1h"),
        },
        "title": S.BACKTEST_DERIVE_RULE,
        "message": f"Derived preference · {indicator} · {pair_u}",
    }
