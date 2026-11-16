"""Dialog geometry prefs round-trip."""

from __future__ import annotations

from pathlib import Path

from trendalgo.device.dialog_geometry import load_dialog_geometry, save_dialog_geometry
from trendalgo.device.results_pair_prefs import load_pair_filters, save_pair_filters
from trendalgo.device.views.lts_board_model import cap_board_rows


def test_dialog_geometry_roundtrip(tmp_path: Path) -> None:
    save_dialog_geometry(tmp_path, "scan_bt_settings", width=1000, height=700, maximized=True)
    block = load_dialog_geometry(tmp_path, "scan_bt_settings")
    assert block is not None
    assert block["width"] == 1000
    assert block["maximized"] is True


def test_pair_filters_roundtrip(tmp_path: Path) -> None:
    save_pair_filters(tmp_path, "AAPL/USD", {"min_net_pct": 5})
    assert load_pair_filters(tmp_path, "aapl/usd")["min_net_pct"] == 5


def test_cap_board_rows() -> None:
    coins = [{"symbol": str(i)} for i in range(100)]
    assert len(cap_board_rows(coins, max_symbols=80)) == 80
