"""Color ranks: equal values share one color."""

from __future__ import annotations

from trendalgo.device.scanner_heat import rank_hex_colors


def test_all_zeros_same_green() -> None:
    colors = rank_hex_colors([0.0, 0.0, 0.0], invert=True)
    assert colors[0] is not None
    assert colors[0] == colors[1] == colors[2]
    # Best for invert (lowest) → green channel high
    assert int(colors[0][3:5], 16) >= 0x90


def test_ties_share_color_distinct_from_other() -> None:
    colors = rank_hex_colors([1.0, 2.0, 1.0], invert=True)
    assert colors[0] == colors[2]
    assert colors[0] != colors[1]


def test_all_hundred_wins_same_green() -> None:
    colors = rank_hex_colors([100.0, 100.0, 100.0], invert=False)
    assert colors[0] == colors[1] == colors[2]
    assert int(colors[0][3:5], 16) >= 0x90  # type: ignore[index]
