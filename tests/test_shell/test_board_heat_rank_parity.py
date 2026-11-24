"""AV-G-BRD3 — rank heat color ladder matches PySide scanner_heat stops."""

from __future__ import annotations

from trendalgo.device.scanner_heat import rank_hex_colors


def test_rank_hex_best_is_green() -> None:
    colors = rank_hex_colors([1.0, 2.0, 3.0])
    assert colors[2] == "#16A34A"
    assert colors[0] == "#DC2626"


def test_rank_hex_invert_flips_best() -> None:
    colors = rank_hex_colors([1.0, 3.0], invert=True)
    assert colors[0] == "#16A34A"
    assert colors[1] == "#DC2626"
