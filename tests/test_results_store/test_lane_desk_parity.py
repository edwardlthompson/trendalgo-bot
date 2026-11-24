"""TradFi/Forex desk export parity (AV-G5)."""

from __future__ import annotations

import json
from pathlib import Path

from trendalgo.results_store.board_export import load_lane_board
from trendalgo.results_store.desk_export import needs_alpaca_cta


def test_forex_board_exports_bot_vs_bh_and_source(tmp_path: Path) -> None:
    (tmp_path / "lts_scan_rows_forex.json").write_text(
        json.dumps(
            {
                "rows": [
                    {
                        "pair": "EUR/USD",
                        "gain": 0.5,
                        "bot_vs_bh_pct": 1.25,
                        "ohlcv_source": "algospecial",
                        "exchange": "algospecial",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    rows = load_lane_board(tmp_path, lane="forex", tab="qualified")
    assert len(rows) == 1
    assert rows[0]["bot_vs_bh_pct"] == 1.25
    assert rows[0]["ohlcv_source"] == "algospecial"


def test_needs_alpaca_cta_false_for_crypto(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("PYTEST_CURRENT_TEST", "1")
    assert needs_alpaca_cta(tmp_path, "crypto") is False
