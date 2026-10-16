"""Look tests (offscreen Qt): palette, header and tabs, icons, the saved look, and OS follow.

Skipped when PySide6 or pytest-qt is missing, like the other Qt tests. No window shows.
"""

from __future__ import annotations

import os
from collections.abc import Iterator

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
pytest.importorskip("PySide6")
pytest.importorskip("pytestqt")

from PySide6.QtCore import Qt  # noqa: E402
from PySide6.QtGui import QPalette  # noqa: E402
from PySide6.QtWidgets import QApplication, QLabel  # noqa: E402
from pytestqt.qtbot import QtBot  # noqa: E402

from trendalgo.device import design_tokens as T  # noqa: E402
from trendalgo.device import icons  # noqa: E402
from trendalgo.device import strings as S  # noqa: E402
from trendalgo.device.appearance import follow_color_scheme, saved_appearance  # noqa: E402
from trendalgo.device.context import DeviceContext  # noqa: E402
from trendalgo.device.icons import NAV_GLYPHS, nav_icon, render_svg, window_icon  # noqa: E402
from trendalgo.device.profile import write_json  # noqa: E402
from trendalgo.device.theme import active_mode, apply_theme  # noqa: E402
from trendalgo.device.views.main_window import MainWindow  # noqa: E402
from trendalgo.device.views.settings_page import SettingsPage  # noqa: E402
from trendalgo.device.workers import WorkerPool  # noqa: E402


@pytest.fixture
def look(qapp: QApplication) -> Iterator[QApplication]:
    yield qapp
    apply_theme(qapp, "light")


def _color(app: QApplication, role: QPalette.ColorRole) -> str:
    return app.palette().color(role).name()


def test_the_dark_look_paints_the_window_and_the_accent(look: QApplication) -> None:
    apply_theme(look, "dark")
    assert active_mode() == "dark"
    assert _color(look, QPalette.ColorRole.Window) == T.DARK["background"].lower()
    apply_theme(look, "light", T.ACCENT_PRESETS[1])
    assert active_mode() == "light"
    assert _color(look, QPalette.ColorRole.Window) == T.LIGHT["background"].lower()
    assert _color(look, QPalette.ColorRole.Link) == T.ACCENT_PRESETS[1]


def test_the_main_window_shows_primary_tabs_and_more(
    qtbot: QtBot,
    ctx: DeviceContext,
    pool: WorkerPool,
    look: QApplication,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from trendalgo.device.nav_layout import NAV_CATALOG

    window = MainWindow(ctx, pool)
    qtbot.addWidget(window)
    assert window._more.text() == S.NAV_MORE
    # Wide pack: every catalog tab visible, More hidden.
    monkeypatch.setattr(window, "_catalog_widths", lambda: [40] * len(NAV_CATALOG))
    window._navbar.setFixedWidth(2000)
    window._rebuild_nav(force=True)
    labels = [window._nav.tabText(index) for index in range(window._nav.count())]
    assert labels[:5] == [
        S.NAV_PORTFOLIO,
        S.NAV_ALERTS,
        S.NAV_SCANNER,
        S.NAV_BACKTESTS,
        S.NAV_STATUS,
    ]
    assert window._nav.count() == len(NAV_CATALOG)
    assert window._more.isHidden()
    assert all(not window._nav.tabIcon(index).isNull() for index in range(window._nav.count()))
    # Narrow pack: overflow only under More.
    monkeypatch.setattr(window, "_catalog_widths", lambda: [100] * len(NAV_CATALOG))
    window._navbar.setFixedWidth(280)
    window._rebuild_nav(force=True)
    assert not window._more.isHidden()
    overflow = {action.text() for action in window._menu.actions()}
    assert overflow
    assert len(overflow) + window._nav.count() == len(NAV_CATALOG)


def test_the_nav_row_shows_host_badge_without_brand_header(
    qtbot: QtBot, ctx: DeviceContext, pool: WorkerPool
) -> None:
    window = MainWindow(ctx, pool)
    qtbot.addWidget(window)
    badge = window.findChild(QLabel, "badge")
    brand = window.findChild(QLabel, "brandName")
    assert badge is not None and badge.text() == S.BADGE_NO_HOST
    assert brand is None
    assert window.windowTitle() == S.APP_TITLE


def test_tab_icons_are_redrawn_when_the_look_changes(
    qtbot: QtBot, ctx: DeviceContext, pool: WorkerPool, look: QApplication
) -> None:
    apply_theme(look, "light")
    window = MainWindow(ctx, pool)
    qtbot.addWidget(window)
    before = window._nav.tabIcon(0).pixmap(20, 20).toImage()
    apply_theme(look, "dark")
    after = window._nav.tabIcon(0).pixmap(20, 20).toImage()
    assert before != after


def test_saving_the_look_in_settings_writes_it_and_applies_it(
    qtbot: QtBot, ctx: DeviceContext, look: QApplication
) -> None:
    page = SettingsPage(ctx)
    qtbot.addWidget(page)
    page._owner.setText("owner-1")
    page._theme.setCurrentIndex(page._theme.findData("dark"))
    page._accent.setCurrentIndex(page._accent.findData(T.ACCENT_PRESETS[0]))
    page.save()
    assert saved_appearance(ctx) == ("dark", T.ACCENT_PRESETS[0])
    assert active_mode() == "dark"
    assert _color(look, QPalette.ColorRole.Link) == T.ACCENT_PRESETS[0]


def test_settings_shows_the_saved_look(qtbot: QtBot, ctx: DeviceContext) -> None:
    write_json(
        ctx.settings_path,
        {"owner_id": "owner-1", "host_url": "", "theme": "light", "accent": T.ACCENT_PRESETS[3]},
    )
    page = SettingsPage(ctx)
    qtbot.addWidget(page)
    assert page._theme.currentData() == "light"
    assert page._accent.currentData() == T.ACCENT_PRESETS[3]


def test_a_missing_or_broken_file_gives_the_default_look(ctx: DeviceContext) -> None:
    assert saved_appearance(ctx) == ("system", "")
    ctx.settings_path.write_text("[1, 2]", encoding="utf-8")
    assert saved_appearance(ctx) == ("system", "")


def test_a_windows_color_change_reapplies_the_saved_look(
    ctx: DeviceContext, look: QApplication
) -> None:
    write_json(
        ctx.settings_path,
        {"owner_id": "owner-1", "host_url": "", "theme": "dark", "accent": ""},
    )
    apply_theme(look, "light")
    follow_color_scheme(look, ctx)
    look.styleHints().colorSchemeChanged.emit(Qt.ColorScheme.Dark)
    assert active_mode() == "dark"


def test_the_window_and_tab_icons_load(look: QApplication, monkeypatch: pytest.MonkeyPatch) -> None:
    assert not window_icon().isNull()
    for name in NAV_GLYPHS:
        assert not nav_icon(name, T.LIGHT["onSurfaceVariant"]).isNull()
    monkeypatch.setattr(icons, "_asset_folders", lambda: [])
    assert not window_icon().isNull()


def test_bad_svg_draws_a_blank_square_not_a_crash(look: QApplication) -> None:
    pixmap = render_svg("<not-svg", 16)
    assert pixmap.width() == 16
    assert pixmap.height() == 16
