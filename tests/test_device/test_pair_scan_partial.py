"""Live partial All-TA results I/O."""

from __future__ import annotations

from pathlib import Path

from trendalgo.device.pair_scan_partial import (
    clear_partial_rows,
    read_partial_rows,
    write_partial_rows,
)


def test_write_read_ranks_by_net(tmp_path: Path) -> None:
    write_partial_rows(
        tmp_path,
        [
            {"indicator": "A", "net_pct": 1.0},
            {"indicator": "B", "net_pct": 9.0},
            {"indicator": "C", "net_pct": 3.0},
        ],
    )
    rows = read_partial_rows(tmp_path)
    assert rows is not None
    assert [r["indicator"] for r in rows] == ["B", "C", "A"]
    clear_partial_rows(tmp_path)
    assert read_partial_rows(tmp_path) is None
