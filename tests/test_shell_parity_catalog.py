"""Parity catalog docs must stay aligned with Avalonia shell inventory map."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INVENTORY = ROOT / "docs" / "PRODUCT_SURFACE_INVENTORY.md"
CATALOG = ROOT / "shell" / "TrendAlgo.Shell" / "Models" / "ParityCatalog.cs"
PUBLISH = ROOT / "scripts" / "packaging" / "publish-avalonia-shell.ps1"


def test_inventory_lists_required_p0_surfaces() -> None:
    text = INVENTORY.read_text(encoding="utf-8")
    for needle in (
        "Dashboard",
        "Crypto desk",
        "TradFi desk",
        "Forex desk",
        "Results Workbook",
        "Settings",
        "Wizards",
    ):
        assert needle in text


def test_parity_catalog_covers_lane_desks() -> None:
    src = CATALOG.read_text(encoding="utf-8")
    for desk in ('"crypto"', '"tradfi"', '"forex"', '"workbook"', '"settings"', '"wizards"'):
        assert desk in src


def test_publish_script_lists_tri_os_rids() -> None:
    text = PUBLISH.read_text(encoding="utf-8")
    for rid in ("win-x64", "linux-x64", "osx-arm64"):
        assert rid in text
