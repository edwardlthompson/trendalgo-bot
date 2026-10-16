"""Local bot cards for the Status page. Host controls enable when a host is linked."""

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from trendalgo.device import strings as S
from trendalgo.device.rows import BotRow


class BotCardList(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(8)
        self._note = QLabel(S.STATUS_HOST_CONTROLS)
        self._note.setObjectName("hint")
        self._note.setWordWrap(True)
        self._layout.addWidget(self._note)
        self._host_controls = False
        self._on_command: Callable[[str, str], None] | None = None

    def set_host_controls(
        self,
        enabled: bool,
        *,
        on_command: Callable[[str, str], None] | None = None,
    ) -> None:
        self._host_controls = enabled
        self._on_command = on_command

    def set_bots(self, bots: list[BotRow]) -> None:
        while self._layout.count() > 1:
            item = self._layout.takeAt(1)
            if item is None:
                break
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
        for bot in bots:
            self._layout.addWidget(_card(bot, self._host_controls, self._on_command))


def _card(
    bot: BotRow,
    host_controls: bool,
    on_command: Callable[[str, str], None] | None,
) -> QFrame:
    frame = QFrame()
    frame.setObjectName("panel")
    column = QVBoxLayout(frame)
    title = QLabel(f"{bot.label} · {bot.pair}")
    title.setObjectName("sectionTitle")
    detail = QLabel(
        S.STATUS_BOT_CARD_DENSE.format(
            state=bot.state,
            strategy=bot.strategy,
            equity=bot.equity,
            realized=bot.realized,
            unrealized=bot.unrealized,
        )
    )
    detail.setObjectName("hint")
    detail.setWordWrap(True)
    actions = QHBoxLayout()
    for label, action in (
        (S.STATUS_ACTION_PLAY, "resume"),
        (S.STATUS_ACTION_PAUSE, "pause"),
        (S.STATUS_ACTION_DELETE, "delete"),
    ):
        button = QPushButton(label)
        enabled = host_controls and on_command is not None
        button.setEnabled(enabled)
        tip = S.STATUS_ACTION_HOST_TIP if not enabled else label
        button.setToolTip(tip)
        button.setAccessibleDescription(tip)
        if enabled and on_command is not None:
            button.clicked.connect(
                lambda _checked=False, a=action, bid=bot.label: on_command(a, bid)
            )
        actions.addWidget(button)
    actions.addStretch(1)
    column.addWidget(title)
    column.addWidget(detail)
    column.addLayout(actions)
    return frame
