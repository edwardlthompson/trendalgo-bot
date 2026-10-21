"""Saved exchange-key inventory table for Settings."""

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from trendalgo.device import strings as S
from trendalgo.device.secrets_vault import VaultEntry, VaultSecretStore
from trendalgo.exchanges.registry import load_registry


class ExchangeKeysInventory(QWidget):
    """List vaulted keys with Update / Test / Remove row actions."""

    def __init__(
        self,
        vault: VaultSecretStore,
        *,
        on_update: Callable[[str], None],
        on_test: Callable[[str], None],
        on_delete: Callable[[str], None],
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._vault = vault
        self._on_update = on_update
        self._on_test = on_test
        self._on_delete = on_delete
        self._empty = QLabel(S.SETTINGS_KEYS_EMPTY)
        self._empty.setObjectName("hint")
        self._empty.setWordWrap(True)
        self._table = QTableWidget(0, 4)
        self._table.setObjectName("settingsKeysInventory")
        self._table.setHorizontalHeaderLabels(
            (
                S.SETTINGS_KEYS_COL_EXCHANGE,
                S.SETTINGS_KEYS_COL_SCOPE,
                S.SETTINGS_KEYS_COL_STATE,
                "",
            )
        )
        self._table.verticalHeader().setVisible(False)
        self._table.setSelectionMode(QTableWidget.SelectionMode.NoSelection)
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._table.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self._table.horizontalHeader().setStretchLastSection(True)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)
        title = QLabel(S.SETTINGS_KEYS_SAVED)
        title.setObjectName("hint")
        layout.addWidget(title)
        layout.addWidget(self._empty)
        layout.addWidget(self._table)
        self.reload()

    def reload(self) -> None:
        entries = self._vault.list_entries()
        brands = {e.id: e.brand for e in load_registry().exchanges}
        self._table.setRowCount(0)
        self._empty.setVisible(not entries)
        self._table.setVisible(bool(entries))
        for entry in entries:
            self._add_row(entry, brands.get(entry.exchange_id, entry.exchange_id))

    def _add_row(self, entry: VaultEntry, brand: str) -> None:
        row = self._table.rowCount()
        self._table.insertRow(row)
        self._table.setItem(row, 0, QTableWidgetItem(brand))
        scope = (
            S.SETTINGS_KEYS_SCOPE_TRADE if entry.scope == "trade" else S.SETTINGS_KEYS_SCOPE_QUERY
        )
        self._table.setItem(row, 1, QTableWidgetItem(scope))
        state = S.SETTINGS_KEYS_VERIFIED if entry.verified_at else S.SETTINGS_KEYS_UNVERIFIED
        self._table.setItem(row, 2, QTableWidgetItem(state))
        actions = QWidget()
        row_lay = QHBoxLayout(actions)
        row_lay.setContentsMargins(0, 0, 0, 0)
        row_lay.setSpacing(4)
        eid = entry.exchange_id
        upd = QPushButton(S.SETTINGS_KEYS_UPDATE)
        tst = QPushButton(S.SETTINGS_KEYS_TEST)
        rem = QPushButton(S.SETTINGS_KEYS_DELETE)
        upd.clicked.connect(lambda _c=False, i=eid: self._on_update(i))
        tst.clicked.connect(lambda _c=False, i=eid: self._on_test(i))
        rem.clicked.connect(lambda _c=False, i=eid: self._on_delete(i))
        row_lay.addWidget(upd)
        row_lay.addWidget(tst)
        row_lay.addWidget(rem)
        row_lay.addStretch(1)
        self._table.setCellWidget(row, 3, actions)
