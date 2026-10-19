"""Coin-specific Secret Sauce study dialog (never the TA glossary)."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from trendalgo.device import strings as S
from trendalgo.device.views.widgets import read_only_table


def show_secret_sauce_study(
    parent: QWidget,
    row: dict[str, Any],
    *,
    coin: dict[str, Any] | None = None,
    on_create_bot: Callable[[dict[str, str], str], str] | None = None,
) -> None:
    dossier = row.get("heartbeat_dossier")
    if not isinstance(dossier, dict):
        params = row.get("params") if isinstance(row.get("params"), dict) else {}
        dossier = params.get("heartbeat_dossier") if isinstance(params, dict) else None
    dialog = QDialog(parent)
    symbol = str((coin or {}).get("symbol") or row.get("symbol") or "")
    name = str(row.get("indicator") or S.SECRET_SAUCE_LABEL)
    dialog.setWindowTitle(S.SECRET_SAUCE_STUDY_TITLE.format(name=name, symbol=symbol or "—"))
    dialog.setMinimumSize(520, 460)
    layout = QVBoxLayout(dialog)
    if bool(row.get("ss_lab_pending")):
        empty = QLabel(S.SECRET_SAUCE_PENDING)
        empty.setWordWrap(True)
        layout.addWidget(empty)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)
        dialog.exec()
        return

    if not isinstance(dossier, dict):
        empty = QLabel(S.SECRET_SAUCE_STUDY_EMPTY)
        empty.setWordWrap(True)
        layout.addWidget(empty)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)
        dialog.exec()
        return

    formula = str(dossier.get("formula_en") or "")
    anti = str(dossier.get("anti_cheat") or "")
    meta = QLabel(
        S.SECRET_SAUCE_STUDY_META.format(
            pair=str((coin or {}).get("pair") or row.get("symbol") or "—"),
            tf=str(row.get("timeframe") or "—"),
            train=float(dossier.get("train_coverage") or 0) * 100.0,
            hold=float(dossier.get("holdout_coverage") or 0) * 100.0,
        )
    )
    meta.setWordWrap(True)
    regime = row.get("regime") if isinstance(row.get("regime"), dict) else None
    if regime is None and isinstance(dossier.get("regime"), dict):
        regime = dossier.get("regime")
    regime_lbl = _regime_label(regime)
    votes_lbl = _votes_label(regime)
    formula_box = QTextEdit()
    formula_box.setReadOnly(True)
    formula_box.setPlainText(formula)
    formula_box.setMaximumHeight(100)
    enter_lbl = QLabel(_side_line(S.SECRET_SAUCE_ENTER, dossier.get("entry_conjuncts")))
    enter_lbl.setWordWrap(True)
    exit_lbl = QLabel(_side_line(S.SECRET_SAUCE_EXIT, dossier.get("exit_conjuncts")))
    exit_lbl.setWordWrap(True)
    anti_lbl = QLabel(anti)
    anti_lbl.setObjectName("hint")
    anti_lbl.setWordWrap(True)
    hits = list(dossier.get("swing_hits") or [])
    exit_hits = list(dossier.get("exit_hits") or [])
    indexes = list(dossier.get("oracle_entry_indexes") or [])
    exit_indexes = list(dossier.get("oracle_exit_indexes") or [])
    table = read_only_table(
        [
            S.SECRET_SAUCE_COL_SWING,
            S.SECRET_SAUCE_COL_ENTRY,
            S.SECRET_SAUCE_COL_FIRED,
            S.SECRET_SAUCE_COL_EXIT,
            S.SECRET_SAUCE_COL_EXIT_FIRED,
        ],
        "secret-sauce-coverage",
    )
    table.setRowCount(max(len(hits), len(indexes), 1))
    for i, idx in enumerate(indexes):
        fired = bool(hits[i]) if i < len(hits) else False
        ex_idx = exit_indexes[i] if i < len(exit_indexes) else "—"
        ex_fired = bool(exit_hits[i]) if i < len(exit_hits) else False
        table.setItem(i, 0, QTableWidgetItem(str(i + 1)))
        table.setItem(i, 1, QTableWidgetItem(str(idx)))
        table.setItem(i, 2, QTableWidgetItem(S.SECRET_SAUCE_YES if fired else S.SECRET_SAUCE_NO))
        table.setItem(i, 3, QTableWidgetItem(str(ex_idx)))
        table.setItem(i, 4, QTableWidgetItem(S.SECRET_SAUCE_YES if ex_fired else S.SECRET_SAUCE_NO))
    nets = QLabel(
        S.SECRET_SAUCE_STUDY_NETS.format(
            name=name,
            sauce=float(row.get("net_pct") or 0.0),
            bh=float(((coin or {}).get("backtest_buy_hold") or {}).get("net_pct") or 0.0),
            oracle=float(((coin or {}).get("backtest_oracle_max") or {}).get("net_pct") or 0.0),
        )
    )
    nets.setWordWrap(True)
    layout.addWidget(meta)
    if regime_lbl is not None:
        layout.addWidget(regime_lbl)
    if votes_lbl is not None:
        layout.addWidget(votes_lbl)
    layout.addWidget(QLabel(S.SECRET_SAUCE_FORMULA))
    layout.addWidget(formula_box)
    layout.addWidget(enter_lbl)
    layout.addWidget(exit_lbl)
    layout.addWidget(anti_lbl)
    layout.addWidget(QLabel(S.SECRET_SAUCE_COVERAGE))
    layout.addWidget(table, 1)
    layout.addWidget(nets)
    row_btns = QHBoxLayout()
    copy_btn = QPushButton(S.SECRET_SAUCE_COPY)
    copy_btn.clicked.connect(lambda _c=False: _copy(formula_box.toPlainText(), dialog))
    row_btns.addWidget(copy_btn)
    if on_create_bot is not None:
        create = QPushButton(S.SECRET_SAUCE_CREATE_BOT)
        create.clicked.connect(lambda _c=False: _create(on_create_bot, row, coin or {}, dialog))
        row_btns.addWidget(create)
    row_btns.addStretch(1)
    layout.addLayout(row_btns)
    buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
    buttons.rejected.connect(dialog.reject)
    layout.addWidget(buttons)
    dialog.exec()


def _regime_label(regime: dict[str, Any] | None) -> QLabel | None:
    if not isinstance(regime, dict):
        return None
    squeeze = " · squeeze" if regime.get("squeeze") else ""
    lbl = QLabel(
        S.SECRET_SAUCE_REGIME.format(
            structural=str(regime.get("structural") or "—"),
            volatility=str(regime.get("volatility") or "—"),
            direction=str(regime.get("direction") or "—"),
            squeeze=squeeze,
            confidence=float(regime.get("structural_confidence") or 0.0),
        )
    )
    lbl.setWordWrap(True)
    return lbl


def _votes_label(regime: dict[str, Any] | None) -> QLabel | None:
    if not isinstance(regime, dict):
        return None
    votes = regime.get("votes") if isinstance(regime.get("votes"), dict) else {}
    yes = S.SECRET_SAUCE_YES
    no = S.SECRET_SAUCE_NO
    lbl = QLabel(
        S.SECRET_SAUCE_REGIME_VOTES.format(
            adx=yes if votes.get("adx") else no,
            er=yes if votes.get("er") else no,
            chop=yes if votes.get("chop") else no,
            ribbon=yes if votes.get("ribbon") else no,
        )
    )
    lbl.setObjectName("hint")
    lbl.setWordWrap(True)
    return lbl


def _side_line(label: str, conjuncts: object) -> str:
    if not isinstance(conjuncts, list) or not conjuncts:
        return f"{label}: —"
    parts = []
    for c in conjuncts:
        if isinstance(c, dict):
            parts.append(f"{c.get('feature')} {c.get('op')} {c.get('value')}")
    return f"{label}: " + (" AND ".join(parts) if parts else "—")


def _copy(text: str, parent: QWidget) -> None:
    from PySide6.QtWidgets import QApplication

    QApplication.clipboard().setText(text)
    parent.setWindowTitle(parent.windowTitle())


def _create(
    on_create_bot: Callable[[dict[str, str], str], str],
    row: dict[str, Any],
    coin: dict[str, Any],
    parent: QWidget,
) -> None:
    pair = str(coin.get("pair") or f"{row.get('symbol') or 'BTC'}/USD")
    prefill = {
        "strategy_id": str(row.get("strategy_id") or "GEN_SECRET_1"),
        "indicator": "Secret Sauce",
        "params": str(row.get("params") or {}),
        "requires_backtest": "true",
        "timeframe": str(row.get("timeframe") or "1h"),
    }
    note = on_create_bot(prefill, pair)
    if note:
        from PySide6.QtWidgets import QMessageBox

        QMessageBox.information(parent, S.SECRET_SAUCE_CREATE_BOT, note)
