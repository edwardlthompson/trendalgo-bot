"""Plan builder page: build the bot list, check it, and save a new plan version on this PC."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from trendalgo.device import strings as S
from trendalgo.device.context import DeviceContext
from trendalgo.device.fields import TIMEFRAMES
from trendalgo.device.host_actions import send_plan_bundle
from trendalgo.device.host_session import try_open_host_client
from trendalgo.device.plan_model import (
    STAKE_FIXED,
    STAKE_PERCENT,
    BotSpec,
    build_bundle,
    check_plan,
    load_plan,
    next_plan_version,
    plan_document,
    validate_bot,
)
from trendalgo.device.profile import ProfileError, read_json, write_json
from trendalgo.device.settings_model import settings_from_document
from trendalgo.device.views.searchable_picker import indicator_picker, pair_picker
from trendalgo.device.views.widgets import (
    EmptyState,
    TailFill,
    clear_problem,
    field,
    fill_table,
    mark_primary,
    page_header,
    problem_label,
    read_only_table,
    show_problem,
)


class PlanPage(QWidget):
    def __init__(self, ctx: DeviceContext, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._ctx = ctx
        self._version = 0
        self._bots: list[BotSpec] = []
        self._load_failed = False
        self._problem = problem_label()
        self._status = QLabel()
        self._name = QLineEdit()
        self._pair = pair_picker()
        self._timeframe = QComboBox()
        self._timeframe.addItems(list(TIMEFRAMES))
        self._indicator = indicator_picker()
        self._stake_mode = QComboBox()
        self._stake_mode.addItem(S.PLAN_STAKE_FIXED, STAKE_FIXED)
        self._stake_mode.addItem(S.PLAN_STAKE_PERCENT, STAKE_PERCENT)
        self._stake_mode.currentIndexChanged.connect(lambda _i: self._sync_stake_help())
        self._stake = QLineEdit("100")
        self._stake_help = QLabel(S.PLAN_STAKE_HELP)
        self._stake_help.setObjectName("hint")
        self._stake_help.setWordWrap(True)
        self._stop = QLineEdit("5")
        self._add = QPushButton(S.PLAN_ADD)
        self._add.clicked.connect(lambda _checked=False: self._add_bot())
        self._apply = QPushButton(S.PLAN_APPLY)
        self._apply.clicked.connect(lambda _checked=False: self._apply_bot())
        self._remove = QPushButton(S.PLAN_REMOVE)
        self._remove.clicked.connect(lambda _checked=False: self._remove_bot())
        self._save = QPushButton(S.PLAN_SAVE)
        self._save.clicked.connect(lambda _checked=False: self._save_plan())
        self._send = mark_primary(QPushButton(S.PLAN_SEND))
        self._send.clicked.connect(lambda _checked=False: self._send_plan())
        self._empty = EmptyState(S.PLAN_EMPTY_TITLE, S.PLAN_EMPTY_BODY)
        self._table = read_only_table(S.PLAN_HEADERS, S.PLAN_TITLE)
        self._table.itemSelectionChanged.connect(self._on_select)
        self._load()

        top = Qt.AlignmentFlag.AlignTop
        first = QHBoxLayout()
        first.addWidget(field(S.PLAN_NAME, self._name, S.PLAN_NAME_HELP), 1, top)
        first.addWidget(field(S.BACKTEST_PAIR, self._pair, S.BACKTEST_PAIR_HELP), 1, top)
        first.addWidget(field(S.PLAN_TIMEFRAME, self._timeframe), 1, top)
        second = QHBoxLayout()
        second.addWidget(field(S.PLAN_INDICATOR, self._indicator), 1, top)
        second.addWidget(field(S.PLAN_STAKE_MODE, self._stake_mode, S.PLAN_STAKE_MODE_HELP), 1, top)
        stake_box = QWidget()
        stake_col = QVBoxLayout(stake_box)
        stake_col.setContentsMargins(0, 0, 0, 0)
        stake_col.addWidget(QLabel(S.PLAN_STAKE))
        stake_col.addWidget(self._stake)
        self._stake.setAccessibleName(S.PLAN_STAKE)
        stake_col.addWidget(self._stake_help)
        second.addWidget(stake_box, 1, top)
        second.addWidget(field(S.PLAN_STOP, self._stop, S.PLAN_STOP_HELP), 1, top)
        actions = QHBoxLayout()
        actions.addWidget(self._add)
        actions.addWidget(self._apply)
        actions.addWidget(self._remove)
        actions.addStretch(1)
        actions.addWidget(self._save)
        actions.addWidget(self._send)
        layout = QVBoxLayout(self)
        layout.addWidget(page_header(S.PLAN_TITLE, S.PLAN_SUBTITLE))
        layout.addWidget(self._problem)
        layout.addLayout(first)
        layout.addLayout(second)
        layout.addLayout(actions)
        layout.addWidget(self._status)
        layout.addWidget(self._empty)
        layout.addWidget(self._table)
        self._fill = TailFill(layout, self._table)
        self._sync_stake_help()
        self._refresh()

    def prefill_from_fleet(self, fields: dict[str, str]) -> None:
        """Fill the add-bot form from a fleet top-row mapping (does not add or save)."""
        self._name.setText(fields.get("name", ""))
        self._pair.setText(fields.get("pair", ""))
        tf = fields.get("timeframe", "")
        idx = self._timeframe.findText(tf)
        if idx >= 0:
            self._timeframe.setCurrentIndex(idx)
        indicator = fields.get("indicator", "")
        if indicator:
            self._indicator.setCurrentText(indicator)
        self._stake.setText(fields.get("stake", ""))
        self._stop.setText(fields.get("stop", ""))
        clear_problem(self._problem)

    def add_bot_from_fields(self, fields: dict[str, str]) -> tuple[bool, str]:
        """Prefill and add one bot. Returns (ok, status_or_error)."""
        self.prefill_from_fleet(fields)
        if not str(fields.get("indicator") or "").strip():
            return False, S.SCANNER_CREATE_BOT_PARTIAL
        spec, problems = self._read_spec()
        if spec is None:
            show_problem(self._problem, " ".join(problems))
            return False, " ".join(problems)
        clashes = check_plan([*self._bots, spec])
        if clashes:
            show_problem(self._problem, " ".join(clashes))
            return False, " ".join(clashes)
        self._bots.append(spec)
        self._name.clear()
        clear_problem(self._problem)
        msg = S.SCANNER_CREATE_BOT_DONE.format(name=spec.name)
        self._status.setText(msg)
        self._refresh()
        return True, msg

    def _load(self) -> None:
        try:
            self._version, self._bots = load_plan(read_json(self._ctx.plan_path))
        except ProfileError as exc:
            self._load_failed = True
            show_problem(self._problem, f"{exc} {S.PLAN_LOAD_BLOCKED}")

    def _stake_mode_value(self) -> str:
        return str(self._stake_mode.currentData() or STAKE_FIXED)

    def _sync_stake_help(self) -> None:
        if self._stake_mode_value() == STAKE_PERCENT:
            self._stake_help.setText(S.PLAN_STAKE_PCT_HELP)
        else:
            self._stake_help.setText(S.PLAN_STAKE_HELP)

    def _read_spec(self) -> tuple[BotSpec | None, list[str]]:
        return validate_bot(
            name=self._name.text(),
            pair=self._pair.text(),
            timeframe=self._timeframe.currentText(),
            indicator=self._indicator.text(),
            stake=self._stake.text(),
            trailing_stop=self._stop.text(),
            stake_mode=self._stake_mode_value(),
        )

    def _add_bot(self) -> None:
        spec, problems = self._read_spec()
        if spec is None:
            show_problem(self._problem, " ".join(problems))
            return
        clashes = check_plan([*self._bots, spec])
        if clashes:
            show_problem(self._problem, " ".join(clashes))
            return
        self._bots.append(spec)
        self._name.clear()
        clear_problem(self._problem)
        self._status.setText(S.PLAN_BOT_ADDED.format(name=spec.name))
        self._refresh()

    def _apply_bot(self) -> None:
        row = self._table.currentRow()
        if not 0 <= row < len(self._bots):
            return
        spec, problems = self._read_spec()
        if spec is None:
            show_problem(self._problem, " ".join(problems))
            return
        others = [bot for index, bot in enumerate(self._bots) if index != row]
        clashes = check_plan([*others, spec])
        if clashes:
            show_problem(self._problem, " ".join(clashes))
            return
        self._bots[row] = spec
        clear_problem(self._problem)
        self._status.setText(S.PLAN_BOT_UPDATED.format(name=spec.name))
        self._refresh()
        self._table.selectRow(row)

    def _remove_bot(self) -> None:
        row = self._table.currentRow()
        if not 0 <= row < len(self._bots):
            return
        removed = self._bots.pop(row)
        self._status.setText(S.PLAN_BOT_REMOVED.format(name=removed.name))
        self._refresh()

    def _on_select(self) -> None:
        row = self._table.currentRow()
        if 0 <= row < len(self._bots):
            bot = self._bots[row]
            self._name.setText(bot.name)
            self._pair.setText(bot.pair)
            tf = self._timeframe.findText(bot.timeframe)
            if tf >= 0:
                self._timeframe.setCurrentIndex(tf)
            self._indicator.setCurrentText(bot.indicator)
            mode_index = self._stake_mode.findData(bot.stake_mode)
            if mode_index >= 0:
                self._stake_mode.setCurrentIndex(mode_index)
            if bot.stake_mode == STAKE_PERCENT:
                self._stake.setText(f"{bot.equity_pct:g}")
            else:
                self._stake.setText(f"{bot.stake_usd:g}")
            self._stop.setText(f"{bot.trailing_stop_pct:g}")
            self._sync_stake_help()
        self._sync_buttons()

    def _save_plan(self) -> None:
        if self._load_failed:
            return
        problems = check_plan(self._bots)
        if problems:
            show_problem(self._problem, " ".join(problems))
            return
        try:
            owner = self._owner_id()
        except ProfileError as exc:
            show_problem(self._problem, str(exc))
            return
        if owner is None:
            show_problem(self._problem, S.PLAN_NEEDS_OWNER)
            return
        version = next_plan_version(self._version)
        try:
            write_json(self._ctx.plan_path, plan_document(version, self._bots))
        except OSError as exc:
            show_problem(self._problem, S.SAVE_FAILED.format(reason=exc.strerror or "disk error"))
            return
        self._version = version
        bundle = build_bundle(self._bots, owner_id=owner, plan_version=version)
        digest = str(bundle["header"]["bundle_hash"])[:12]
        clear_problem(self._problem)
        saved = S.PLAN_SAVED.format(version=version, count=len(self._bots), digest=digest)
        self._status.setText(saved)

    def _send_plan(self) -> None:
        if self._load_failed:
            return
        problems = check_plan(self._bots)
        if problems:
            show_problem(self._problem, " ".join(problems))
            return
        try:
            owner = self._owner_id()
        except ProfileError as exc:
            show_problem(self._problem, str(exc))
            return
        if owner is None:
            show_problem(self._problem, S.PLAN_NEEDS_OWNER)
            return
        client = try_open_host_client(self._ctx.settings_path)
        if client is None:
            show_problem(self._problem, S.PLAN_SEND_NO_HOST)
            return
        version = self._version if self._version else next_plan_version(0)
        if not self._version:
            try:
                write_json(self._ctx.plan_path, plan_document(version, self._bots))
            except OSError as exc:
                show_problem(
                    self._problem, S.SAVE_FAILED.format(reason=exc.strerror or "disk error")
                )
                return
            self._version = version
        bundle = build_bundle(self._bots, owner_id=owner, plan_version=version)
        ok, code = send_plan_bundle(client, bundle)
        if not ok:
            message = {
                "host_unreachable": S.PLAN_SEND_UNREACHABLE,
                "plan_stale": S.PLAN_SEND_STALE,
                "plan_refused": S.PLAN_SEND_REFUSED,
                "host.pin_mismatch": S.PLAN_SEND_REFUSED,
                "host.pin_missing": S.PLAN_SEND_NO_HOST,
            }.get(code, S.PLAN_SEND_REFUSED)
            show_problem(self._problem, message)
            return
        digest = code.split(":")[-1] if code.startswith("sent:") else ""
        sent_version = int(code.split(":")[1]) if code.startswith("sent:") else version
        clear_problem(self._problem)
        self._status.setText(S.PLAN_SENT.format(version=sent_version, digest=digest))

    def _owner_id(self) -> str | None:
        settings = settings_from_document(read_json(self._ctx.settings_path))
        return settings.owner_id if settings is not None else None

    def _sync_buttons(self) -> None:
        selected = 0 <= self._table.currentRow() < len(self._bots)
        self._remove.setEnabled(selected)
        self._apply.setEnabled(selected and not self._load_failed)
        ready = bool(self._bots) and not self._load_failed
        self._save.setEnabled(ready)
        self._send.setEnabled(ready)

    def _stake_cell(self, bot: BotSpec) -> str:
        if bot.stake_mode == STAKE_PERCENT:
            return f"{bot.equity_pct:g}%"
        return f"${bot.stake_usd:,.2f}"

    def _refresh(self) -> None:
        fill_table(
            self._table,
            [
                (
                    bot.name,
                    bot.pair,
                    bot.timeframe,
                    bot.indicator,
                    self._stake_cell(bot),
                    f"{bot.trailing_stop_pct:g}",
                )
                for bot in self._bots
            ],
        )
        has_bots = bool(self._bots)
        self._table.setVisible(has_bots)
        self._fill.update(has_bots)
        self._empty.setVisible(not has_bots)
        self._sync_buttons()
