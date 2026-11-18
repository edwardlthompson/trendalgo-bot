"""Lockfile must never pull known-malicious / typosquat packages."""

from __future__ import annotations

from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
_LOCK = _REPO / "uv.lock"
_FORBIDDEN = (
    "agent-framework",
    "gateio-sdk",
    "gateio-v4",
    "gateio-client",
    "gateio-ws",
    "gatepay-sdk-python",
)


def test_uv_lock_excludes_malicious_pypi_names() -> None:
    text = _LOCK.read_text(encoding="utf-8")
    for name in _FORBIDDEN:
        assert f'name = "{name}"' not in text, f"{name} must not appear in uv.lock"
