"""Health filter is a typed min field, not a combo."""

from __future__ import annotations

import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
pytest.importorskip("PySide6")

from trendalgo.device.views.scanner_column_filter_row import (  # noqa: E402
    HealthMinEdit,
    ScannerColumnFilterRow,
)


def test_health_min_edit_roundtrip(qtbot) -> None:
    row = ScannerColumnFilterRow()
    qtbot.addWidget(row)
    assert isinstance(row.health_min, HealthMinEdit)
    row.health_min.setValue(72)
    dumped = row.dump()
    assert dumped["health_min"] == "72"
    row.load({"health_min": "65"})
    assert row.health_min.floor() == 65
    row.load({"health_min": ""})
    assert row.health_min.floor() is None
