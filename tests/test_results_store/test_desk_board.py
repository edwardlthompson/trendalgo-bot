"""Desk board mutations — watch / buy picks / create-bot (gap depth)."""

from __future__ import annotations

import json
from pathlib import Path

from trendalgo.results_store.desk_board import (
    create_bot_from_fields,
    load_buy_picks_surface,
    toggle_watch,
)


def test_toggle_watch_roundtrip(tmp_path: Path) -> None:
    first = toggle_watch(tmp_path, "btc/usd", lane="crypto")
    assert first["watched"] is True
    assert first["count"] == 1
    second = toggle_watch(tmp_path, "BTC/USD", lane="crypto")
    assert second["watched"] is False
    assert second["count"] == 0


def test_buy_picks_from_lts(tmp_path: Path) -> None:
    (tmp_path / "lts_scan_rows.json").write_text(
        json.dumps(
            {
                "rows": [
                    {
                        "pair": "ETH/USD",
                        "symbol": "ETH",
                        "bot_best_net_pct": 4.0,
                        "market_context": {
                            "ok": True,
                            "regime_label": "trend",
                            "consensus": {"signal": "Buy", "score": 0.8, "confidence": 0.7},
                            "structure": {"nearest_sr_name": "S1", "confluence": 2},
                            "risk": {"rr_to_r1": 1.5},
                        },
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    data = load_buy_picks_surface(tmp_path)
    assert data["count"] == 1
    assert data["rows"][0]["pair"] == "ETH/USD"


def test_create_bot_appends_plan(tmp_path: Path) -> None:
    out = create_bot_from_fields(
        tmp_path, pair="BTC/USD", indicator="RSI", timeframe="1h", stake_usd=10
    )
    assert out["ok"] is True
    assert out["count"] == 1
    plan = json.loads((tmp_path / "plan.json").read_text(encoding="utf-8"))
    assert plan["bots"][0]["pair"] == "BTC/USD"
