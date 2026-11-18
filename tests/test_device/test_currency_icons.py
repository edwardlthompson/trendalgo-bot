"""Fiat currency icon pool for Forex composites."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest


def test_ensure_currency_icon_writes_pool(tmp_path: Path, qtbot: Any, monkeypatch: Any) -> None:
    pytest.importorskip("PySide6")
    from trendalgo.device import currency_icons as ci

    monkeypatch.setattr(ci, "_MODULE_REPO", tmp_path)
    ci.clear_currency_icon_cache()
    path = ci.ensure_currency_icon("EUR", size=64)
    assert path is not None and path.is_file()
    assert path.name == "EUR.png"
    assert ci.currency_icon_path("EUR") == path


def test_forex_icon_uses_currency_pool(tmp_path: Path, qtbot: Any, monkeypatch: Any) -> None:
    pytest.importorskip("PySide6")
    from trendalgo.device import currency_icons as ci
    from trendalgo.device import lane_icons as li

    monkeypatch.setattr(ci, "_MODULE_REPO", tmp_path)
    monkeypatch.setattr(li, "_FX_POOL_SEEDED", False)
    ci.clear_currency_icon_cache()
    pix = li.icon_for_row(tmp_path, "EURUSD", lane="forex", pair="EUR/USD", fetch_remote=False)
    assert not pix.isNull()
    assert (tmp_path / "branding" / "assets" / "currencies" / "EUR.png").is_file()
    assert (tmp_path / "branding" / "assets" / "currencies" / "USD.png").is_file()


def test_currency_codes_cover_universe() -> None:
    from trendalgo.device.currency_icons import CURRENCY_MARKS, currency_codes_for_universe

    codes = set(currency_codes_for_universe())
    assert "EUR" in codes and "USD" in codes and "JPY" in codes
    assert set(CURRENCY_MARKS).issubset(codes)
