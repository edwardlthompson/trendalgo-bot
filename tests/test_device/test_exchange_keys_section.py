"""Exchange API keys settings section: labels, popup height, public/private fields."""

from __future__ import annotations

from PySide6.QtWidgets import QLabel, QLineEdit, QMessageBox

from trendalgo.device import strings as S
from trendalgo.device.views.exchange_keys_section import (
    ExchangeKeysSection,
    exchange_keys_section_for_tests,
)
from trendalgo.device.views.widgets import configure_combo_popup
from trendalgo.device.wizard.credentials import CredentialError, MemoryCredentialStore


def test_exchange_keys_section_labels_public_and_private(qtbot) -> None:
    section = exchange_keys_section_for_tests()
    qtbot.addWidget(section)
    labels = {lab.text() for lab in section.findChildren(QLabel)}
    assert S.SETTINGS_KEYS_PUBLIC in labels
    assert S.SETTINGS_KEYS_PRIVATE in labels
    assert S.SETTINGS_KEYS_EXCHANGE in labels
    assert S.SETTINGS_KEYS_SCOPE in labels
    assert section._key.accessibleName() == S.SETTINGS_KEYS_PUBLIC
    assert section._secret.accessibleName() == S.SETTINGS_KEYS_PRIVATE
    assert section._key.placeholderText() == S.SETTINGS_KEYS_PUBLIC_PLACEHOLDER
    assert section._secret.placeholderText() == S.SETTINGS_KEYS_PRIVATE_PLACEHOLDER
    assert section._key.echoMode() == QLineEdit.EchoMode.Password
    assert section._secret.echoMode() == QLineEdit.EchoMode.Password


def test_scope_and_exchange_combos_open_tall_enough(qtbot) -> None:
    section = exchange_keys_section_for_tests()
    qtbot.addWidget(section)
    assert section._scope.maxVisibleItems() >= section._scope.count()
    assert section._exchange.maxVisibleItems() >= section._exchange.count()
    assert section._scope.view().minimumHeight() >= 28 * section._scope.count()
    assert section._exchange.view().minimumHeight() >= 28 * min(section._exchange.count(), 8)


def test_configure_combo_popup_sets_visible_rows(qtbot) -> None:
    from PySide6.QtWidgets import QComboBox

    box = QComboBox()
    qtbot.addWidget(box)
    for i in range(5):
        box.addItem(f"Item {i}", i)
    configure_combo_popup(box, visible=3)
    assert box.maxVisibleItems() == 3
    assert box.view().minimumHeight() >= 28 * 3


def test_save_shows_success_clears_fields_and_lists_inventory(qtbot, monkeypatch) -> None:  # noqa: ANN001
    dialogs: list[tuple[str, str]] = []

    def _info(parent, title, text, *args, **kwargs):  # noqa: ANN001
        del parent, args, kwargs
        dialogs.append((str(title), str(text)))
        return QMessageBox.StandardButton.Ok

    monkeypatch.setattr(QMessageBox, "information", _info)
    section = exchange_keys_section_for_tests()
    qtbot.addWidget(section)
    eid = str(section._exchange.itemData(0))
    brand = section._brand_for(eid)
    section._key.setText("pub-key-fixture")
    section._secret.setText("priv-secret-fixture")
    section._save()
    assert section._key.text() == ""
    assert section._secret.text() == ""
    assert section._vault.read_entry(eid) is not None
    assert S.SETTINGS_KEYS_UNVERIFIED in section._status.text()
    assert len(dialogs) == 1
    assert dialogs[0][0] == S.SETTINGS_KEYS_SAVE_OK_TITLE
    assert brand in dialogs[0][1]
    assert "Credential Manager" in dialogs[0][1]
    assert section._inventory._table.rowCount() == 1
    assert section._save_btn.isEnabled() is True


def test_save_failure_keeps_fields_and_shows_error(qtbot) -> None:  # noqa: ANN001
    class _BoomStore(MemoryCredentialStore):
        def write(self, target: str, secret: str) -> None:
            raise CredentialError("Credential Manager could not save it (Windows error 5).")

    section = ExchangeKeysSection(store=_BoomStore())
    qtbot.addWidget(section)
    section._key.setText("keep-public")
    section._secret.setText("keep-secret")
    section._save()
    assert section._key.text() == "keep-public"
    assert section._secret.text() == "keep-secret"
    assert "Could not save keys" in section._status.text()
    assert "Windows error 5" in section._status.text()
    assert section._vault.read_entry(section._exchange_id()) is None
    assert section._save_btn.isEnabled() is True
