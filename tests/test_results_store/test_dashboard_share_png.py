"""AV-G-DSH4 — dashboard PNG export."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
pytest.importorskip("PySide6")

from trendalgo.results_store.desk_share import share_dashboard_png  # noqa: E402


def test_share_dashboard_png(tmp_path: Path) -> None:
    out = share_dashboard_png(tmp_path)
    assert out["kind"] == "dashboard"
    assert out["rows"] >= 1
    path = Path(out["path"])
    assert path.is_file()
    assert path.suffix == ".png"
    assert path.stat().st_size > 32
