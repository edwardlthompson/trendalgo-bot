"""Dense TF prefs, resample-from-1m, ETA history, strategy filter."""

from __future__ import annotations

import os
from pathlib import Path

import pandas as pd
import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
pytest.importorskip("PySide6")
pytest.importorskip("pytestqt")

from pytestqt.qtbot import QtBot  # noqa: E402

from trendalgo.backtest.heartbeat_tf import (  # noqa: E402
    HEARTBEAT_TIMEFRAMES,
    needs_1m_base,
    normalize_timeframes,
    sort_timeframes,
)
from trendalgo.backtest.ohlcv_resample import frames_from_base, resample_ohlcv  # noqa: E402
from trendalgo.device import strings as S  # noqa: E402
from trendalgo.device.scan_bt_prefs import (  # noqa: E402
    ScanBtPrefs,
    enabled_strategies,
    load_scan_bt_prefs,
    save_scan_bt_prefs,
    selected_timeframes,
)
from trendalgo.device.scan_time_history import (  # noqa: E402
    TimingSample,
    estimate_coin_seconds,
    load_history,
    record_sample,
)
from trendalgo.device.settings_layout_prefs import (  # noqa: E402
    SECTION_IDS,
    factory_defaults,
    load_settings_layout,
    save_settings_layout,
)
from trendalgo.device.views.scan_bt_settings_dialog import (  # noqa: E402
    ScanBacktestSettingsDialog,
)


def test_needs_1m_base_detects_subhour() -> None:
    assert needs_1m_base(("1h", "4h")) is False
    assert needs_1m_base(("5m", "1h")) is True
    assert needs_1m_base(("1m",)) is True


def test_normalize_and_sort_mixed_tfs() -> None:
    raw = ["4h", "1m", "bogus", "1h", "1m"]
    assert normalize_timeframes(raw) == ["4h", "1m", "1h"]
    assert sort_timeframes(["4h", "1m", "15m", "1h"]) == ("1m", "15m", "1h", "4h")


def test_frames_from_1m_to_5m_and_1h() -> None:
    idx = pd.date_range("2026-01-01", periods=120, freq="1min", tz="UTC")
    frame = pd.DataFrame(
        {
            "open": range(120),
            "high": range(1, 121),
            "low": range(120),
            "close": range(120),
            "volume": [1.0] * 120,
        },
        index=idx,
    )
    out = frames_from_base(frame, ["1m", "5m", "1h"])
    assert len(out["1m"]) == 120
    assert len(out["5m"]) == 24
    assert len(out["1h"]) == 2
    with pytest.raises(ValueError):
        resample_ohlcv(out["1h"], "1m")


def test_scan_bt_prefs_round_trip(tmp_path: Path) -> None:
    prefs = ScanBtPrefs(
        timeframes=["1h", "5m", "12h"],
        strategy_denylist=["RSI"],
        bt_signal_set="all_ta",
    )
    save_scan_bt_prefs(tmp_path, prefs)
    loaded = load_scan_bt_prefs(tmp_path)
    assert "5m" in loaded.timeframes
    assert "12h" in loaded.timeframes
    assert "RSI" in loaded.strategy_denylist
    assert selected_timeframes(loaded)[0] == "5m"


def test_enabled_strategies_honors_denylist() -> None:
    all_names = enabled_strategies([])
    assert len(all_names) > 5
    blocked = enabled_strategies([all_names[0]])
    assert all_names[0] not in blocked
    assert len(blocked) == len(all_names) - 1


def test_scan_time_history_eta_improves_with_samples(tmp_path: Path) -> None:
    hist = load_history(tmp_path)
    seed = estimate_coin_seconds(hist, n_strategies=10, n_timeframes=24, had_subhour=False)
    for i in range(5):
        record_sample(
            tmp_path,
            TimingSample(
                elapsed_s=12.0,
                n_strategies=10,
                n_timeframes=24,
                had_subhour=False,
                ts=float(i),
            ),
        )
    hist2 = load_history(tmp_path)
    assert len(hist2.samples) == 5
    est = estimate_coin_seconds(hist2, n_strategies=10, n_timeframes=12, had_subhour=False)
    assert est > 0
    assert est < seed * 2


def test_settings_layout_defaults_cover_all_sections(tmp_path: Path) -> None:
    prefs = factory_defaults()
    assert {p.id for p in prefs.placements} == set(SECTION_IDS)
    save_settings_layout(tmp_path, prefs)
    loaded = load_settings_layout(tmp_path)
    assert len(loaded.placements) == len(SECTION_IDS)


def test_settings_grid_reflow_pushes_and_compacts() -> None:
    from trendalgo.device.portfolio_layout_prefs import Placement
    from trendalgo.device.settings_grid_fit import (
        cols_for_pixels,
        reflow_content_heights,
        rows_for_pixels,
    )

    assert rows_for_pixels(200, cell_h=50.0, gap_px=8) >= 4
    assert cols_for_pixels(400, cell_w=40.0, gap_px=8, cols=24) >= 8
    placements = [
        Placement(id="a", col=0, row=0, w=12, h=2),
        Placement(id="b", col=0, row=2, w=12, h=2),
        Placement(id="c", col=12, row=0, w=12, h=2),
    ]
    # Expand a → b packs below a; c stays in its column.
    out = reflow_content_heights(placements, {"a": 6, "b": 2, "c": 2}, cols=24)
    by_id = {p.id: p for p in out}
    assert by_id["a"].h == 6
    assert by_id["a"].row == 0
    assert by_id["b"].row == by_id["a"].h
    assert by_id["c"].col == 12
    assert by_id["c"].row == 0
    # Collapse a → b fills the gap at top of column.
    compact = reflow_content_heights(out, {"a": 2, "b": 2, "c": 2}, cols=24)
    by2 = {p.id: p for p in compact}
    assert by2["a"].row == 0
    assert by2["b"].row == by2["a"].h
    # DnD pin: drop b at row 0 col 0; a packs below; gap filled.
    pinned = reflow_content_heights(
        [
            Placement(id="a", col=0, row=0, w=12, h=2),
            Placement(id="b", col=0, row=0, w=12, h=2),
            Placement(id="c", col=12, row=4, w=12, h=2),
        ],
        {"a": 2, "b": 2, "c": 2},
        cols=24,
        pin_id="b",
    )
    by3 = {p.id: p for p in pinned}
    assert by3["b"].row == 0
    assert by3["a"].row == by3["b"].h
    assert by3["c"].row == 0  # fills empty space at top of right column
    # Auto-widen: content-driven width_cols grows a.
    wide = reflow_content_heights(
        placements,
        {"a": 2, "b": 2, "c": 2},
        cols=24,
        width_cols={"a": 16, "b": 8, "c": 10},
    )
    assert {p.id: p.w for p in wide}["a"] == 16


def test_settings_square_48_col_limits_dead_space() -> None:
    """48-col square cells keep ceil waste under ~one cell on wide windows."""
    from trendalgo.device.portfolio_grid_snap import Rect, cell_size, rect_to_pixels
    from trendalgo.device.settings_grid_fit import rows_for_pixels
    from trendalgo.device.settings_layout_prefs import factory_defaults

    prefs = factory_defaults()
    assert prefs.grid.cols == 48
    assert prefs.grid.row_px == 0.0
    assert "actions" not in {p.id for p in prefs.placements}
    need_h = 232
    cw, ch = cell_size(
        1600,
        900,
        prefs.grid.cols,
        prefs.grid.rows,
        prefs.grid.gap_px,
        fixed_row_px=prefs.grid.row_px,
    )
    assert cw == ch
    rows = rows_for_pixels(need_h, ch, prefs.grid.gap_px)
    _x, _y, _w, slot_h = rect_to_pixels(Rect(0, 0, 24, rows), cw, ch, prefs.grid.gap_px)
    assert slot_h >= need_h
    assert slot_h - need_h < ch + prefs.grid.gap_px


def test_settings_layout_v2_resets_to_v3_square_defaults(tmp_path: Path) -> None:
    from trendalgo.device.profile import write_json
    from trendalgo.device.settings_layout_prefs import load_settings_layout, prefs_path

    write_json(
        prefs_path(tmp_path),
        {
            "layout_version": 2,
            "edit_mode": True,
            "grid": {"cols": 24, "rows": 48, "gap_px": 8, "row_px": 32.0},
            "placements": [
                {"id": "connection", "col": 0, "row": 0, "w": 6, "h": 4},
                {"id": "actions", "col": 0, "row": 4, "w": 6, "h": 2},
            ],
        },
    )
    loaded = load_settings_layout(tmp_path)
    assert loaded.layout_version >= 3
    assert loaded.grid.cols == 48
    assert loaded.grid.row_px == 0.0
    assert "actions" not in {p.id for p in loaded.placements}
    assert len(loaded.placements) == len(SECTION_IDS)


def test_default_timeframes_are_hours_only(tmp_path: Path) -> None:
    prefs = load_scan_bt_prefs(tmp_path)
    assert list(selected_timeframes(prefs)) == list(HEARTBEAT_TIMEFRAMES)
    assert needs_1m_base(selected_timeframes(prefs)) is False


def test_scan_bt_settings_dialog_wires_dump_keys(tmp_path: Path, qtbot: QtBot) -> None:
    dlg = ScanBacktestSettingsDialog(tmp_path, show_signal_set=True, n_coins=3)
    qtbot.addWidget(dlg)
    assert dlg.windowTitle()
    assert dlg._eta.text()
    dlg._tf_boxes["5m"].setChecked(True)
    dlg._tf_boxes["1h"].setChecked(True)
    for tf, box in dlg._tf_boxes.items():
        if tf not in ("5m", "1h"):
            box.setChecked(False)
    dlg._save()
    loaded = load_scan_bt_prefs(tmp_path)
    assert "5m" in loaded.timeframes
    assert "1h" in loaded.timeframes
    assert needs_1m_base(tuple(loaded.timeframes)) is True
    assert loaded.bt_signal_set in ("3commas", "all_ta")
    for box in dlg._tf_boxes.values():
        box.setChecked(False)
    dlg._save()
    assert dlg._eta.text() == S.SCAN_BT_NO_TFS
