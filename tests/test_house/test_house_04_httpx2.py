"""HOUSE-04: httpx2 is the correct Starlette TestClient dependency (not a typo)."""

from __future__ import annotations

import re
from pathlib import Path


def test_dev_extra_pins_httpx2_not_httpx() -> None:
    text = Path("pyproject.toml").read_text(encoding="utf-8")
    pins = re.findall(r'"((?:httpx2?|httpcore2?)[^"]*)"', text)
    assert any(p.startswith("httpx2>=") for p in pins)
    assert not any(p.startswith("httpx>=") for p in pins)
