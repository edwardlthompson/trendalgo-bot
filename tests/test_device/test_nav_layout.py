"""Unit tests for responsive nav packing."""

from __future__ import annotations

from trendalgo.device.nav_layout import NAV_CATALOG, NavItem, pack_nav


def test_pack_nav_wide_fits_all() -> None:
    widths = [80] * len(NAV_CATALOG)
    visible, overflow = pack_nav(
        NAV_CATALOG, available_width=10_000, tab_widths=widths, more_width=64
    )
    assert overflow == []
    assert visible == list(NAV_CATALOG)


def test_pack_nav_narrow_overflows_into_more() -> None:
    widths = [100] * len(NAV_CATALOG)
    visible, overflow = pack_nav(NAV_CATALOG, available_width=280, tab_widths=widths, more_width=64)
    assert visible
    assert overflow
    assert len(visible) + len(overflow) == len(NAV_CATALOG)
    assert all(isinstance(item, NavItem) for item in visible + overflow)
