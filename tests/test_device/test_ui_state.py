"""Nav page persistence (first open → Portfolio, then last tab)."""

from __future__ import annotations

from pathlib import Path

from trendalgo.device.nav_layout import ALERTS, BACKTESTS, GLOSSARY, PORTFOLIO, SCANNER
from trendalgo.device.profile import write_json
from trendalgo.device.ui_state import default_nav_page, load_nav_page, save_nav_page, ui_state_path


def test_first_open_defaults_to_portfolio(tmp_path: Path) -> None:
    assert load_nav_page(tmp_path) is None
    assert default_nav_page(tmp_path) == PORTFOLIO


def test_save_and_restore_nav_page(tmp_path: Path) -> None:
    save_nav_page(tmp_path, BACKTESTS)
    assert load_nav_page(tmp_path) == BACKTESTS
    assert default_nav_page(tmp_path) == BACKTESTS
    save_nav_page(tmp_path, GLOSSARY)
    assert default_nav_page(tmp_path) == GLOSSARY
    save_nav_page(tmp_path, ALERTS)
    assert default_nav_page(tmp_path) == ALERTS


def test_legacy_int_nav_page_maps_scanner(tmp_path: Path) -> None:
    write_json(ui_state_path(tmp_path), {"nav_page": 1})
    assert load_nav_page(tmp_path) == SCANNER


def test_invalid_nav_page_ignored(tmp_path: Path) -> None:
    save_nav_page(tmp_path, 999)
    assert load_nav_page(tmp_path) is None
