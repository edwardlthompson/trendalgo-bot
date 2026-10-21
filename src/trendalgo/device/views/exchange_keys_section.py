"""Settings section: vault exchange keys inventory + add/rotate form."""

from __future__ import annotations

from PySide6.QtCore import QTimer
from PySide6.QtGui import QHideEvent, QShowEvent
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from trendalgo.device import strings as S
from trendalgo.device.secrets_vault import VaultEntry, VaultSecretStore, memory_vault_for_tests
from trendalgo.device.theme import active_mode
from trendalgo.device.theme_css import colors_for
from trendalgo.device.views.exchange_keys_inventory import ExchangeKeysInventory
from trendalgo.device.views.widgets import configure_combo_popup, field, mark_primary
from trendalgo.device.wizard.credentials import CredentialStore
from trendalgo.exchanges.private_budget import budget_snapshot
from trendalgo.exchanges.registry import load_registry
from trendalgo.trading.key_verify import success_dialog_text, verify_exchange_keys


class ExchangeKeysSection(QWidget):
    def __init__(
        self,
        *,
        store: CredentialStore | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._vault = VaultSecretStore(store)
        self._vault.bind_registry()
        self._inventory = ExchangeKeysInventory(
            self._vault,
            on_update=self._begin_update,
            on_test=self._test_exchange,
            on_delete=self._delete_exchange,
        )
        self._exchange = QComboBox()
        for entry in load_registry().exchanges:
            self._exchange.addItem(entry.brand, entry.id)
        configure_combo_popup(self._exchange)
        self._scope = QComboBox()
        self._scope.addItem(S.SETTINGS_KEYS_SCOPE_QUERY, "query")
        self._scope.addItem(S.SETTINGS_KEYS_SCOPE_TRADE, "trade")
        configure_combo_popup(self._scope)
        self._key = QLineEdit()
        self._key.setEchoMode(QLineEdit.EchoMode.Password)
        self._key.setPlaceholderText(S.SETTINGS_KEYS_PUBLIC_PLACEHOLDER)
        self._secret = QLineEdit()
        self._secret.setEchoMode(QLineEdit.EchoMode.Password)
        self._secret.setPlaceholderText(S.SETTINGS_KEYS_PRIVATE_PLACEHOLDER)
        self._status = QLabel(S.SETTINGS_KEYS_NONE)
        self._status.setObjectName("hint")
        self._check = QLabel("")
        self._rate = QLabel(S.SETTINGS_KEYS_RATE_EMPTY)
        self._rate.setObjectName("hint")
        self._rate_timer = QTimer(self)
        self._rate_timer.setInterval(2_000)
        self._rate_timer.timeout.connect(self._refresh_rate)
        save = mark_primary(QPushButton(S.SETTINGS_KEYS_SAVE))
        save.setMinimumHeight(44)
        save.clicked.connect(lambda _c=False: self._save())
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)
        help_lbl = QLabel(S.SETTINGS_KEYS_HELP)
        help_lbl.setWordWrap(True)
        help_lbl.setObjectName("hint")
        layout.addWidget(help_lbl)
        layout.addWidget(self._inventory)
        add_lbl = QLabel(S.SETTINGS_KEYS_ADD)
        add_lbl.setObjectName("hint")
        layout.addWidget(add_lbl)
        layout.addWidget(field(S.SETTINGS_KEYS_EXCHANGE, self._exchange))
        layout.addWidget(field(S.SETTINGS_KEYS_SCOPE, self._scope, S.SETTINGS_KEYS_SCOPE_HELP))
        layout.addWidget(field(S.SETTINGS_KEYS_PUBLIC, self._key, S.SETTINGS_KEYS_PUBLIC_HELP))
        layout.addWidget(field(S.SETTINGS_KEYS_PRIVATE, self._secret, S.SETTINGS_KEYS_PRIVATE_HELP))
        row = QHBoxLayout()
        row.setSpacing(8)
        row.addWidget(save)
        row.addStretch(1)
        layout.addLayout(row)
        layout.addWidget(self._check)
        layout.addWidget(self._status)
        layout.addWidget(self._rate)
        self._exchange.currentIndexChanged.connect(lambda _i: self._refresh_status())
        self._refresh_status()

    def showEvent(self, event: QShowEvent) -> None:
        super().showEvent(event)
        self._inventory.reload()
        self._refresh_rate()
        self._rate_timer.start()

    def hideEvent(self, event: QHideEvent) -> None:
        self._rate_timer.stop()
        super().hideEvent(event)

    def _exchange_id(self) -> str:
        return str(self._exchange.currentData())

    def _select_exchange(self, exchange_id: str) -> None:
        index = self._exchange.findData(exchange_id)
        if index >= 0:
            self._exchange.setCurrentIndex(index)

    def _begin_update(self, exchange_id: str) -> None:
        self._select_exchange(exchange_id)
        entry = self._vault.read_entry(exchange_id)
        if entry is not None:
            scope_i = self._scope.findData(entry.scope)
            if scope_i >= 0:
                self._scope.setCurrentIndex(scope_i)
        self._key.clear()
        self._secret.clear()
        self._key.setFocus()
        self._refresh_status()

    def _max_per_min(self) -> int:
        entry = load_registry().by_id(self._exchange_id())
        if entry is None or entry.max_private_calls_per_min is None:
            return 15
        return max(1, int(entry.max_private_calls_per_min))

    def _refresh_rate(self) -> None:
        eid = self._exchange_id()
        if self._vault.read_entry(eid) is None:
            self._rate.setText(S.SETTINGS_KEYS_RATE_EMPTY)
            self._rate.setStyleSheet("")
            return
        snap = budget_snapshot(eid, max_per_min=self._max_per_min())
        used = int(snap["used"])
        max_calls = int(snap["max_calls"])
        self._rate.setText(S.SETTINGS_KEYS_RATE.format(used=used, max=max_calls))
        if int(snap["remaining"]) <= 0:
            err = colors_for(active_mode())["error"]
            self._rate.setStyleSheet(f"color: {err};")
        else:
            self._rate.setStyleSheet("")

    def _refresh_status(self) -> None:
        entry = self._vault.read_entry(self._exchange_id())
        if entry is None:
            self._status.setText(S.SETTINGS_KEYS_NONE)
            self._check.setText("")
            self._refresh_rate()
            return
        state = S.SETTINGS_KEYS_VERIFIED if entry.verified_at else S.SETTINGS_KEYS_UNVERIFIED
        mark = "✓ " if entry.verified_at else ""
        self._check.setText(mark)
        self._status.setText(S.SETTINGS_KEYS_STATUS.format(scope=entry.scope, state=state))
        self._refresh_rate()

    def _save(self) -> None:
        scope = str(self._scope.currentData())
        if scope not in ("query", "trade"):
            scope = "query"
        entry = VaultEntry(
            exchange_id=self._exchange_id(),
            api_key=self._key.text().strip(),
            api_secret=self._secret.text().strip(),
            scope=scope,  # type: ignore[arg-type]
        )
        if not entry.api_key or not entry.api_secret:
            self._status.setText(S.SETTINGS_KEYS_REQUIRED)
            return
        self._vault.write_entry(entry)
        self._key.clear()
        self._secret.clear()
        self._refresh_status()
        self._inventory.reload()

    def _delete_exchange(self, exchange_id: str) -> None:
        brand = exchange_id
        reg = load_registry().by_id(exchange_id)
        if reg is not None:
            brand = reg.brand
        reply = QMessageBox.question(
            self,
            S.SETTINGS_KEYS_DELETE,
            S.SETTINGS_KEYS_DELETE_CONFIRM.format(brand=brand),
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        self._vault.delete_entry(exchange_id)
        if self._exchange_id() == exchange_id:
            self._refresh_status()
        self._inventory.reload()

    def _test_exchange(self, exchange_id: str) -> None:
        self._select_exchange(exchange_id)
        self._test()

    def _test(self) -> None:
        entry = self._vault.read_entry(self._exchange_id())
        if entry is None:
            self._status.setText(S.SETTINGS_KEYS_SAVE_FIRST)
            return
        result = verify_exchange_keys(
            exchange_id=entry.exchange_id,
            scope=entry.scope,
            fetch_balance=lambda: {"total": {}},
        )
        if not result.ok:
            self._check.setText("")
            self._status.setText(result.message)
            return
        updated = VaultEntry(
            exchange_id=entry.exchange_id,
            api_key=entry.api_key,
            api_secret=entry.api_secret,
            scope=entry.scope,
            verified_at=result.verified_at,
        )
        self._vault.write_entry(updated)
        self._check.setText("✓")
        self._refresh_status()
        self._inventory.reload()
        QMessageBox.information(self, S.SETTINGS_KEYS_OK_TITLE, success_dialog_text(result))


def exchange_keys_section_for_tests() -> ExchangeKeysSection:
    vault, mem = memory_vault_for_tests()
    del vault
    return ExchangeKeysSection(store=mem)
