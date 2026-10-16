"""Coin icon path resolution for the Scanner logo column."""

from __future__ import annotations

from pathlib import Path

import pytest

from trendalgo.device.coin_icons import clear_coin_icon_cache, coin_icon_dir, coin_icon_path


def test_coin_icon_path_reads_env_folder(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    png = tmp_path / "BTC.png"
    png.write_bytes(
        b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
        b"\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\xf8\x0f\x00"
        b"\x00\x01\x01\x00\x05\x18\xd8N\x00\x00\x00\x00IEND\xaeB`\x82"
    )
    monkeypatch.setenv("TRENDALGO_COIN_ICONS", str(tmp_path))
    clear_coin_icon_cache()
    assert coin_icon_dir() == tmp_path
    assert coin_icon_path("BTC") == png
    assert coin_icon_path("btc/usd") == png
    assert coin_icon_path("MISSING") is None
