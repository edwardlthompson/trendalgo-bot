"""Coin-specific Secret Sauce study dialog (never the TA glossary)."""

from __future__ import annotations

import html
from collections.abc import Callable
from typing import Any

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTableWidgetItem,
    QToolButton,
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
        _stub(layout, dialog, S.SECRET_SAUCE_PENDING)
        return
    if bool(row.get("ss_unavailable")):
        _stub(layout, dialog, str(row.get("spectrum_note") or S.SECRET_SAUCE_UNAVAILABLE))
        return
    if not isinstance(dossier, dict):
        _stub(layout, dialog, S.SECRET_SAUCE_STUDY_EMPTY)
        return

    formula = str(dossier.get("formula_en") or "")
    anti = str(dossier.get("anti_cheat") or "")
    pair = str((coin or {}).get("pair") or row.get("symbol") or "—")
    tf = str(row.get("timeframe") or "—")
    sauce = float(row.get("net_pct") or 0.0)
    bh = float(((coin or {}).get("backtest_buy_hold") or {}).get("net_pct") or 0.0)
    oracle = float(((coin or {}).get("backtest_oracle_max") or {}).get("net_pct") or 0.0)

    # 1) Hero — bold pair · TF · Replay Net %
    hero = QLabel(
        f"<span style='font-size:15pt'><b>{html.escape(pair)}</b> · {html.escape(tf)}</span><br/>"
        f"<span style='font-size:18pt'><b>{html.escape(name)} "
        f"{sauce:.2f}%</b></span>"
    )
    hero.setTextFormat(Qt.TextFormat.RichText)
    hero.setWordWrap(True)
    secondary = QLabel(
        f"B&amp;H {bh:.2f}% · Oracle ceiling {oracle:.2f}% · "
        f"train {float(dossier.get('train_coverage') or 0) * 100.0:.0f}% · "
        f"holdout {float(dossier.get('holdout_coverage') or 0) * 100.0:.0f}%"
    )
    secondary.setObjectName("hint")
    secondary.setWordWrap(True)
    layout.addWidget(hero)
    layout.addWidget(secondary)

    # 2) Rule block — Enter / Exit rich lines (formula kept for Copy only)
    rules_title = QLabel(S.SECRET_SAUCE_RULES)
    rules_title.setObjectName("sectionTitle")
    layout.addWidget(rules_title)
    enter_lbl = QLabel(_side_rich(S.SECRET_SAUCE_ENTER, dossier.get("entry_conjuncts")))
    enter_lbl.setTextFormat(Qt.TextFormat.RichText)
    enter_lbl.setWordWrap(True)
    exit_lbl = QLabel(_side_rich(S.SECRET_SAUCE_EXIT, dossier.get("exit_conjuncts")))
    exit_lbl.setTextFormat(Qt.TextFormat.RichText)
    exit_lbl.setWordWrap(True)
    layout.addWidget(enter_lbl)
    layout.addWidget(exit_lbl)

    # 3) Regime chips (muted) + votes as hint
    regime = row.get("regime") if isinstance(row.get("regime"), dict) else None
    if regime is None and isinstance(dossier.get("regime"), dict):
        regime = dossier.get("regime")
    regime_lbl = _regime_label(regime)
    if regime_lbl is not None:
        regime_lbl.setObjectName("hint")
        layout.addWidget(regime_lbl)
    votes_lbl = _votes_label(regime)
    if votes_lbl is not None:
        layout.addWidget(votes_lbl)
    voters = dossier.get("final_voters")
    if isinstance(voters, list) and voters:
        voters_lbl = QLabel(
            S.SECRET_SAUCE_FINAL_VOTERS.format(voters=", ".join(str(v) for v in voters))
        )
        voters_lbl.setObjectName("hint")
        voters_lbl.setWordWrap(True)
        layout.addWidget(voters_lbl)

    # 4) Honesty / anti-cheat collapsed
    anti_summary = QLabel(S.SECRET_SAUCE_ANTI_SUMMARY)
    anti_summary.setObjectName("hint")
    anti_summary.setWordWrap(True)
    layout.addWidget(anti_summary)
    if anti.strip():
        more = QToolButton()
        more.setText(S.SECRET_SAUCE_ANTI_MORE)
        more.setCheckable(True)
        more.setObjectName("hint")
        anti_full = QLabel(anti)
        anti_full.setObjectName("hint")
        anti_full.setWordWrap(True)
        anti_full.setMaximumHeight(0)
        anti_full.hide()

        def _toggle(checked: bool, *, box: QLabel = anti_full, btn: QToolButton = more) -> None:
            box.setVisible(checked)
            box.setMaximumHeight(16777215 if checked else 0)

        more.toggled.connect(_toggle)
        layout.addWidget(more)
        layout.addWidget(anti_full)

    # 5) Residuals
    residual_lbl = _residual_label(dossier)
    if residual_lbl is not None:
        layout.addWidget(residual_lbl)

    # 6) Coverage table (secondary)
    layout.addWidget(QLabel(S.SECRET_SAUCE_COVERAGE))
    table = _coverage_table(dossier)
    layout.addWidget(table, 1)

    # Honesty stubs (LIVE-05) — muted
    from trendalgo.device.views.secret_sauce_study_honesty import honesty_labels

    for lbl in honesty_labels(row, coin):
        layout.addWidget(lbl)

    # 7) Actions
    row_btns = QHBoxLayout()
    copy_btn = QPushButton(S.SECRET_SAUCE_COPY)
    copy_btn.clicked.connect(lambda _c=False: _copy(formula or _formula_plain(dossier), dialog))
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


def _stub(layout: QVBoxLayout, dialog: QDialog, text: str) -> None:
    empty = QLabel(text)
    empty.setWordWrap(True)
    layout.addWidget(empty)
    buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
    buttons.rejected.connect(dialog.reject)
    layout.addWidget(buttons)
    dialog.exec()


def _coverage_table(dossier: dict[str, Any]) -> Any:
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
    return table


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


def _side_rich(label: str, conjuncts: object) -> str:
    if not isinstance(conjuncts, list) or not conjuncts:
        return f"<b>{html.escape(label)}</b>: —"
    parts: list[str] = []
    for c in conjuncts:
        if isinstance(c, dict):
            feat = html.escape(str(c.get("feature") or ""))
            op = html.escape(str(c.get("op") or ""))
            val = html.escape(str(c.get("value") or ""))
            parts.append(f"<b>{feat}</b> {op} <b>{val}</b>")
    joined = " AND ".join(parts) if parts else "—"
    return f"<b>{html.escape(label)}</b>: {joined}"


def _formula_plain(dossier: dict[str, Any]) -> str:
    enter = _side_plain(S.SECRET_SAUCE_ENTER, dossier.get("entry_conjuncts"))
    exit_ = _side_plain(S.SECRET_SAUCE_EXIT, dossier.get("exit_conjuncts"))
    return f"{enter}\n{exit_}"


def _side_plain(label: str, conjuncts: object) -> str:
    if not isinstance(conjuncts, list) or not conjuncts:
        return f"{label}: —"
    parts = []
    for c in conjuncts:
        if isinstance(c, dict):
            parts.append(f"{c.get('feature')} {c.get('op')} {c.get('value')}")
    return f"{label}: " + (" AND ".join(parts) if parts else "—")


def _residual_label(dossier: dict[str, Any]) -> QLabel | None:
    res_e = list(dossier.get("residual_entry_indexes") or [])
    res_x = list(dossier.get("residual_exit_indexes") or [])
    hits = list(dossier.get("residual_feature_hits") or [])
    gap_raw = dossier.get("oracle_gap_net_pct")
    if not res_e and not res_x and gap_raw is None:
        return None
    gap = ""
    try:
        if gap_raw is not None:
            gap = f" · Oracle gap {float(gap_raw):.2f}"
    except (TypeError, ValueError):
        gap = ""
    feat_bits: list[str] = []
    for row in hits[:3]:
        if not isinstance(row, dict):
            continue
        feats = row.get("features") if isinstance(row.get("features"), list) else []
        if feats:
            feat_bits.append(str(feats[0]))
    features = f" · e.g. {', '.join(feat_bits)}" if feat_bits else ""
    lbl = QLabel(
        S.SECRET_SAUCE_RESIDUAL.format(
            n_entry=len(res_e),
            n_exit=len(res_x),
            gap=gap,
            features=features,
        )
    )
    lbl.setObjectName("hint")
    lbl.setWordWrap(True)
    return lbl


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
        "indicator": str(row.get("indicator") or "Secret Sauce Final"),
        "params": str(row.get("params") or {}),
        "requires_backtest": "true",
        "timeframe": str(row.get("timeframe") or "1h"),
    }
    note = on_create_bot(prefill, pair)
    if note:
        from PySide6.QtWidgets import QMessageBox

        QMessageBox.information(parent, S.SECRET_SAUCE_CREATE_BOT, note)
