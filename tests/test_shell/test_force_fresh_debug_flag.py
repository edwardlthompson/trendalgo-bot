"""AV-G-STR10 — force-fresh stays behind TRENDALGO_DEBUG_SCAN."""

from __future__ import annotations

from trendalgo.device.debug_scan import ENV_FLAG, debug_scan_enabled


def test_debug_scan_flag_name() -> None:
    assert ENV_FLAG == "TRENDALGO_DEBUG_SCAN"


def test_debug_scan_enabled_truthy(monkeypatch) -> None:
    monkeypatch.setenv(ENV_FLAG, "1")
    assert debug_scan_enabled() is True
    monkeypatch.setenv(ENV_FLAG, "0")
    assert debug_scan_enabled() is False
