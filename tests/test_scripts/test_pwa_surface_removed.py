"""Assert Phase 2 PWA cleanup: no live modules/web path or ws route module."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_modules_web_absent() -> None:
    assert not (ROOT / "modules" / "web").exists()


def test_web_project_layout_doc_absent() -> None:
    assert not (ROOT / "docs" / "WEB_PROJECT_LAYOUT.md").exists()


def test_api_ws_route_module_absent() -> None:
    assert not (ROOT / "src" / "trendalgo" / "api" / "routes" / "ws.py").exists()


def test_agents_md_has_no_live_modules_web() -> None:
    text = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
    assert "modules/web/" not in text
    assert "examples/web/" not in text
