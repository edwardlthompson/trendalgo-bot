"""Lane icon resolver: lettermarks / FX composites without network."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest


def test_tradfi_lettermark(tmp_path: Path, qtbot: Any) -> None:
    pytest.importorskip("PySide6")
    from trendalgo.device.lane_icons import icon_for_row

    pix = icon_for_row(tmp_path, "AAPL", lane="tradfi", fetch_remote=False)
    assert not pix.isNull()
    assert pix.width() >= 16


def test_tradfi_remote_fetch_caches(tmp_path: Path, qtbot: Any, monkeypatch: Any) -> None:
    pytest.importorskip("PySide6")
    from trendalgo.device import lane_icons as li

    png = (
        b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
        b"\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\xf8\x0f\x00"
        b"\x00\x01\x01\x00\x05\x18\xd8N\x00\x00\x00\x00IEND\xaeB`\x82"
    )

    class _Resp:
        def read(self) -> bytes:
            return png

        def __enter__(self) -> _Resp:
            return self

        def __exit__(self, *args: object) -> None:
            return None

    monkeypatch.setattr(
        li.urllib.request,
        "urlopen",
        lambda *_a, **_k: _Resp(),
    )
    path = li.prefetch_equity_logo(tmp_path, "AAPL")
    assert path is not None and path.is_file()
    # Worker path must not require a QPixmap (thread-safe download only).
    assert li._download_equity_logo("MSFT", tmp_path / "eq_MSFT.png")  # noqa: SLF001
    pix = li.icon_for_row(tmp_path, "AAPL", lane="tradfi", fetch_remote=False)
    assert not pix.isNull()


def test_forex_composite(tmp_path: Path, qtbot: Any) -> None:
    pytest.importorskip("PySide6")
    from trendalgo.device.lane_icons import icon_for_row

    pix = icon_for_row(tmp_path, "EUR", lane="forex", pair="EUR/USD", fetch_remote=False)
    assert not pix.isNull()
