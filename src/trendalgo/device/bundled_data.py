"""Resolve bundled device JSON under checkout or PyInstaller ``_MEIPASS``."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

_DATA = Path(__file__).resolve().parent / "data"


def data_dir() -> Path:
    return _DATA


def bundled_json(name: str) -> dict[str, Any]:
    path = first_bundled_file(name)
    return json.loads(path.read_text(encoding="utf-8"))


def first_bundled_file(name: str) -> Path:
    rel = Path("trendalgo") / "device" / "data" / name
    source = _DATA / name
    for candidate in _candidates(rel, source):
        if candidate.is_file():
            return candidate
    return source


def _candidates(rel: Path, source: Path) -> list[Path]:
    out: list[Path] = []
    meipass = getattr(sys, "_MEIPASS", None)
    if isinstance(meipass, str):
        root = Path(meipass)
        out.append(root / rel)
        out.append(root / "device" / "data" / rel.name)
    out.append(source)
    return out
