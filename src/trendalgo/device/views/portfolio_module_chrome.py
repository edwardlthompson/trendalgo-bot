"""Module chrome: title, export, remove, drag handle, BR resize grip."""

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from trendalgo.device import strings as S

# Modules that already paint their own heading (CoinStats-quiet).
_SELF_TITLED = frozenset({"total_worth", "assets"})


class ModuleChrome(QFrame):
    def __init__(
        self,
        module_id: str,
        title: str,
        body: QWidget,
        *,
        on_export: Callable[[str], None] | None = None,
        on_remove: Callable[[str], None] | None = None,
        edit_mode: bool = False,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.module_id = module_id
        self._title = title
        self._has_export = on_export is not None
        self._has_remove = on_remove is not None
        self.setObjectName("dashModule")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self._self_titled = module_id in _SELF_TITLED

        header = QHBoxLayout()
        header.setContentsMargins(0, 0, 0, 4 if self._self_titled else 6)
        header.setSpacing(6)
        self._handle = QLabel("⠿")
        self._handle.setObjectName("dashMuted")
        self._handle.setCursor(Qt.CursorShape.OpenHandCursor)
        self._handle.setToolTip("Drag to move")
        self._title_lbl = QLabel("" if self._self_titled else title)
        self._title_lbl.setObjectName("dashModuleTitle")
        self._export_btn = QPushButton("⇩")
        self._export_btn.setObjectName("dashIconBtn")
        self._export_btn.setToolTip(S.PORTFOLIO_EXPORT_MODULE)
        if on_export is not None:
            self._export_btn.clicked.connect(lambda _c=False: on_export(module_id))
        self._remove_btn = QPushButton("✕")
        self._remove_btn.setObjectName("dashIconBtn")
        self._remove_btn.setToolTip(S.PORTFOLIO_REMOVE_MODULE)
        if on_remove is not None:
            self._remove_btn.clicked.connect(lambda _c=False: on_remove(module_id))
        header.addWidget(self._handle)
        header.addWidget(self._title_lbl, 1)
        header.addWidget(self._export_btn)
        header.addWidget(self._remove_btn)
        self._header_host = QWidget()
        self._header_host.setLayout(header)

        self._resize_handle = QLabel("◢")
        self._resize_handle.setObjectName("dashResizeGrip")
        self._resize_handle.setFixedSize(18, 18)
        self._resize_handle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._resize_handle.setCursor(Qt.CursorShape.SizeFDiagCursor)
        self._resize_handle.setToolTip(S.PORTFOLIO_RESIZE_MODULE)

        foot = QHBoxLayout()
        foot.setContentsMargins(0, 0, 0, 0)
        foot.setSpacing(0)
        foot.addStretch(1)
        foot.addWidget(self._resize_handle)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 6)
        layout.setSpacing(6)
        layout.addWidget(self._header_host)
        layout.addWidget(body, 1)
        layout.addLayout(foot)
        self.body = body
        self.set_edit_mode(edit_mode)

    @property
    def handle(self) -> QLabel:
        return self._handle

    @property
    def resize_handle(self) -> QLabel:
        return self._resize_handle

    def set_edit_mode(self, editing: bool) -> None:
        self._handle.setVisible(editing)
        self._export_btn.setVisible(editing and self._has_export)
        self._remove_btn.setVisible(editing and self._has_remove)
        self._resize_handle.setVisible(editing)
        if self._self_titled:
            self._header_host.setVisible(editing)
            self._title_lbl.setText(self._title if editing else "")
        else:
            self._header_host.setVisible(True)
