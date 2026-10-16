"""Crash-inbox stub stays disabled (Golden Path GP-8)."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from types import ModuleType

ROOT = Path(__file__).resolve().parents[1]


def _load_crash_inbox() -> ModuleType:
    path = ROOT / "scripts" / "lib" / "crash_inbox.py"
    spec = importlib.util.spec_from_file_location("crash_inbox", path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_check_repo_passes_on_checkout() -> None:
    mod = _load_crash_inbox()
    assert mod.check_repo(ROOT) == []


def test_check_stub_rejects_enabled() -> None:
    mod = _load_crash_inbox()
    errors = mod.check_stub({"enabled": True, "provider": "none"}, "stub.json")
    assert any("enabled" in e for e in errors)


def test_check_stub_rejects_live_dsn() -> None:
    mod = _load_crash_inbox()
    errors = mod.check_stub(
        {"enabled": False, "provider": "glitchtip", "dsn": "https://example.invalid/1"},
        "stub.json",
    )
    assert any("DSN" in e or "endpoint" in e for e in errors)


def test_example_schema_disabled() -> None:
    example = ROOT / "schemas" / "golden-path" / "crash-inbox.example.json"
    data = json.loads(example.read_text(encoding="utf-8"))
    assert data.get("enabled") is False
    assert not (data.get("dsn") or data.get("endpoint"))
