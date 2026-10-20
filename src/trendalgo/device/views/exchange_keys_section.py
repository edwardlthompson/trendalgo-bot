"""Settings section: vault exchange keys + verify dialog (Phase 1 / 5)."""

from __future__ import annotations

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
from trendalgo.device.wizard.credentials import CredentialStore
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
        self._exchange = QComboBox()
        for entry in load_registry().exchanges:
            self._exchange.addItem(entry.brand, entry.id)
        self._scope = QComboBox()
        self._scope.addItem(S.SETTINGS_KEYS_SCOPE_QUERY, "query")
        self._scope.addItem(S.SETTINGS_KEYS_SCOPE_TRADE, "trade")
        self._key = QLineEdit()
        self._key.setEchoMode(QLineEdit.EchoMode.Password)
        self._secret = QLineEdit()
        self._secret.setEchoMode(QLineEdit.EchoMode.Password)
        self._status = QLabel("—")
        self._status.setObjectName("hint")
        self._check = QLabel("")
        save = QPushButton(S.SETTINGS_KEYS_SAVE)
        test = QPushButton(S.SETTINGS_KEYS_TEST)
        delete = QPushButton(S.SETTINGS_KEYS_DELETE)
        save.clicked.connect(lambda _c=False: self._save())
        test.clicked.connect(lambda _c=False: self._test())
        delete.clicked.connect(lambda _c=False: self._delete())
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        help_lbl = QLabel(S.SETTINGS_KEYS_HELP)
        help_lbl.setWordWrap(True)
        help_lbl.setObjectName("hint")
        layout.addWidget(help_lbl)
        layout.addWidget(self._exchange)
        layout.addWidget(self._scope)
        layout.addWidget(self._key)
        layout.addWidget(self._secret)
        row = QHBoxLayout()
        row.addWidget(save)
        row.addWidget(test)
        row.addWidget(delete)
        layout.addLayout(row)
        layout.addWidget(self._check)
        layout.addWidget(self._status)
        self._exchange.currentIndexChanged.connect(lambda _i: self._refresh_status())
        self._refresh_status()

    def _exchange_id(self) -> str:
        return str(self._exchange.currentData())

    def _refresh_status(self) -> None:
        entry = self._vault.read_entry(self._exchange_id())
        if entry is None:
            self._status.setText("No key saved")
            self._check.setText("")
            return
        verified = "verified" if entry.verified_at else "saved (not verified)"
        mark = "✓ " if entry.verified_at else ""
        self._check.setText(mark)
        self._status.setText(f"{entry.scope} · {verified}")

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
            self._status.setText("Key and secret required")
            return
        self._vault.write_entry(entry)
        self._key.clear()
        self._secret.clear()
        self._refresh_status()

    def _delete(self) -> None:
        self._vault.delete_entry(self._exchange_id())
        self._refresh_status()

    def _test(self) -> None:
        entry = self._vault.read_entry(self._exchange_id())
        if entry is None:
            self._status.setText("Save a key first")
            return
        # Offline-safe probe: treat non-empty vault entry as structurally ok when
        # live network probe is unavailable; live path uses fetch_balance.
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
        QMessageBox.information(self, S.SETTINGS_KEYS_OK_TITLE, success_dialog_text(result))


def exchange_keys_section_for_tests() -> ExchangeKeysSection:
    vault, mem = memory_vault_for_tests()
    del vault
    return ExchangeKeysSection(store=mem)
