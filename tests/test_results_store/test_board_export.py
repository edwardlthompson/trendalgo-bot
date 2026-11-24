"""Lane board export for Avalonia LTS grid (AV-G2)."""

from __future__ import annotations

from pathlib import Path

from trendalgo.device.lts_scan_model import save_lts_rows
from trendalgo.results_store.board_export import BOARD_TABS, load_lane_board


def test_board_tabs() -> None:
    assert BOARD_TABS == ("qualified", "watchlist", "logs")


def test_load_lane_board_qualified_from_lts_json(tmp_path: Path) -> None:
    save_lts_rows(
        tmp_path,
        [
            {
                "pair": "BTC/USD",
                "symbol": "BTC",
                "exchange": "kraken",
                "gain": 2.5,
                "volume_score": 0.8,
                "watch": False,
            },
            {
                "pair": "ETH/USD",
                "symbol": "ETH",
                "exchange": "kraken",
                "gain": 1.1,
                "volume_score": 0.4,
                "watch": True,
            },
        ],
        lane="crypto",
    )
    rows = load_lane_board(tmp_path, lane="crypto", tab="qualified")
    assert len(rows) == 2
    assert rows[0]["pair"] == "BTC/USD"
    assert "gain" in rows[0]
    watched = load_lane_board(tmp_path, lane="crypto", tab="watchlist")
    assert len(watched) == 1
    assert watched[0]["pair"] == "ETH/USD"
    logs = load_lane_board(tmp_path, lane="crypto", tab="logs")
    assert logs == []
