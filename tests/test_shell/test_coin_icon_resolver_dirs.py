"""Fallback validation for Avalonia logo dirs (AV-G-BRD1) — mirrors CoinIconResolver."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_branding_coin_or_currency_icon_dirs_exist() -> None:
    coins = ROOT / "branding" / "assets" / "coins"
    currencies = ROOT / "branding" / "assets" / "currencies"
    assert coins.is_dir()
    assert currencies.is_dir()
    pngs = list(coins.glob("*.png")) + list(currencies.glob("*.png"))
    assert pngs, "expected at least one branding PNG for board logos"


def test_sample_currency_icon_resolves_like_shell() -> None:
    currencies = ROOT / "branding" / "assets" / "currencies"
    sample = next(currencies.glob("*.png"), None)
    assert sample is not None
    assert sample.is_file()
