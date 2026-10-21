"""Exchange API keys settings section: labels, popup height, public/private fields."""

from __future__ import annotations

from PySide6.QtWidgets import QLabel, QLineEdit

from trendalgo.device import strings as S
from trendalgo.device.views.exchange_keys_section import exchange_keys_section_for_tests
from trendalgo.device.views.widgets import configure_combo_popup


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
