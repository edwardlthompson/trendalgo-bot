"""Qt smoke for the AI strategies page under More."""

from __future__ import annotations

import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
pytest.importorskip("PySide6")
pytest.importorskip("pytestqt")

from pytestqt.qtbot import QtBot  # noqa: E402

from trendalgo.device.context import DeviceContext  # noqa: E402
from trendalgo.device.views.ai_recommender_page import AiRecommenderPage  # noqa: E402


def test_ai_page_still_constructs_offline(qtbot: QtBot, ctx: DeviceContext) -> None:
    """AI Strategies removed from nav; page module kept for offline/tests."""
    page = AiRecommenderPage(ctx)
    qtbot.addWidget(page)
    assert page._curated.rowCount() >= 0


def test_ai_page_shows_curated_presets(qtbot: QtBot, ctx: DeviceContext) -> None:
    page = AiRecommenderPage(ctx)
    qtbot.addWidget(page)
    page.show()
    assert page._curated.isVisible()
    assert page._curated.rowCount() >= 3
    assert page._curated_empty.isHidden()
    assert page._recs_empty.isVisible()
    assert page._recs.isHidden()
