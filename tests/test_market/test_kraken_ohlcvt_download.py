"""OHLCVT download progress callback emits overall 0–1 fractions."""

from __future__ import annotations

from pathlib import Path
from urllib.error import URLError

import pytest

from trendalgo.market import kraken_ohlcvt_download as mod


def test_download_full_archive_progress_and_join(tmp_path: Path, monkeypatch) -> None:
    events: list[tuple[str, float]] = []

    class _Resp:
        headers = {"Content-Length": "4"}

        def read(self, _n: int = 0) -> bytes:
            if getattr(self, "_done", False):
                return b""
            self._done = True
            return b"abcd"

        def __enter__(self) -> _Resp:
            return self

        def __exit__(self, *_a: object) -> None:
            return None

    def fake_urlopen(req, timeout: int = 0):  # noqa: ANN001
        del timeout
        headers = getattr(req, "headers", {}) or {}
        assert "User-Agent" in headers or "user-agent" in {k.lower() for k in headers}
        return _Resp()

    monkeypatch.setattr(mod.urllib.request, "urlopen", fake_urlopen)
    out = mod.download_full_archive(
        tmp_path,
        on_progress=lambda msg, frac: events.append((msg, frac)),
    )
    assert out.name == mod.OHLCVT_JOINED_NAME
    assert out.is_file()
    assert out.read_bytes() == b"abcd" * 5
    assert events
    assert events[-1][1] == 1.0
    assert any(f >= 0.9 for _, f in events)
    assert any("Joining" in m for m, _ in events)


def test_download_reports_cancel(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(
        mod.urllib.request,
        "urlopen",
        lambda *_a, **_k: (_ for _ in ()).throw(URLError("nope")),
    )
    with pytest.raises(URLError):
        mod.download_full_archive(tmp_path, cancel=lambda: False)
