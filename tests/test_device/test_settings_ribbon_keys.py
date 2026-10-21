"""Settings ribbon (Save / wizards) and saved-keys inventory."""

from __future__ import annotations

import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
pytest.importorskip("PySide6")
pytest.importorskip("pytestqt")

from pytestqt.qtbot import QtBot  # noqa: E402

from trendalgo.device import strings as S  # noqa: E402
from trendalgo.device.context import DeviceContext  # noqa: E402
from trendalgo.device.secrets_vault import VaultEntry, memory_vault_for_tests  # noqa: E402
from trendalgo.device.views.exchange_keys_section import ExchangeKeysSection  # noqa: E402
from trendalgo.device.views.notify_settings import NotifySettingsSection  # noqa: E402
from trendalgo.device.views.settings_page import SettingsPage  # noqa: E402


def test_settings_ribbon_has_save_setup_and_telegram(qtbot: QtBot, ctx: DeviceContext) -> None:
    page = SettingsPage(ctx, on_setup_wizard=lambda: None)
    qtbot.addWidget(page)
    assert page._save.objectName() == "settingsRibbonSave"
    assert page._save.property("role") == "primary"
    assert not page._setup.isHidden()
    assert page._telegram.text() == S.NOTIFY_TELEGRAM_WIZARD
    assert page.findChild(type(page), "settingsActions") is None
    ids = {p.id for p in page._layout_prefs.placements}
    assert "actions" not in ids
    assert page._canvas.surface()._grid.cols == 48
    assert page._canvas.surface()._grid.row_px == 0.0


def test_notify_section_has_no_telegram_wizard_button(qtbot: QtBot, ctx: DeviceContext) -> None:
    from PySide6.QtWidgets import QPushButton

    section = NotifySettingsSection(ctx)
    qtbot.addWidget(section)
    texts = {b.text() for b in section.findChildren(QPushButton)}
    assert S.NOTIFY_TELEGRAM_WIZARD not in texts
    assert S.SETTINGS_SAVE in texts


def test_keys_inventory_lists_update_and_delete(qtbot: QtBot) -> None:
    vault, mem = memory_vault_for_tests()
    vault.bind_registry()
    vault.write_entry(
        VaultEntry(exchange_id="kraken", api_key="pub", api_secret="priv", scope="query")
    )
    section = ExchangeKeysSection(store=mem)
    qtbot.addWidget(section)
    section.show()
    qtbot.waitExposed(section)
    section._inventory.reload()
    assert section._inventory._table.rowCount() == 1
    assert section._inventory._empty.isHidden()
    section._begin_update("kraken")
    assert section._exchange_id() == "kraken"
    assert section._scope.currentData() == "query"
    section._vault.delete_entry("kraken")
    section._inventory.reload()
    assert section._inventory._table.rowCount() == 0
    assert section._inventory._empty.isVisible()


def test_vault_list_entries_returns_saved_only() -> None:
    vault, _mem = memory_vault_for_tests()
    vault.bind_registry()
    assert vault.list_entries() == []
    vault.write_entry(VaultEntry(exchange_id="kraken", api_key="k", api_secret="s", scope="trade"))
    listed = vault.list_entries()
    assert len(listed) == 1
    assert listed[0].exchange_id == "kraken"
    assert listed[0].scope == "trade"
