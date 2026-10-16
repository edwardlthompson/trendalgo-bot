"""Settings page: owner ID, host address, the look, and the setup wizard. Checked before saving."""

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from trendalgo import __version__
from trendalgo.device import strings as S
from trendalgo.device.context import DeviceContext
from trendalgo.device.profile import ProfileError, read_json, write_json
from trendalgo.device.settings_model import (
    ACCENT_CHOICES,
    THEME_CHOICES,
    settings_from_document,
    settings_to_document,
    validate_settings,
)
from trendalgo.device.theme import apply_theme
from trendalgo.device.views.notify_settings import NotifySettingsSection
from trendalgo.device.views.widgets import (
    clear_problem,
    field,
    mark_primary,
    page_header,
    problem_label,
    section_title,
    show_problem,
)

THEME_LABELS = (S.THEME_SYSTEM, S.THEME_LIGHT, S.THEME_DARK)
ACCENT_LABELS = (S.ACCENT_DEFAULT, *S.ACCENT_NAMES)


class SettingsPage(QWidget):
    def __init__(
        self,
        ctx: DeviceContext,
        on_setup_wizard: Callable[[], None] | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._ctx = ctx
        self._on_setup_wizard = on_setup_wizard
        self._owner = QLineEdit()
        self._host = QLineEdit()
        self._host.setPlaceholderText("https://host.example:8443")
        self._cert_pin = QLineEdit()
        self._cert_pin.setPlaceholderText("64-character SHA-256 fingerprint")
        self._theme = _choice_box(THEME_LABELS, THEME_CHOICES)
        self._accent = _choice_box(ACCENT_LABELS, ACCENT_CHOICES)
        self._first_run = QLabel(S.SETTINGS_FIRST_RUN)
        self._problem = problem_label()
        self._status = QLabel()
        self._save = mark_primary(QPushButton(S.SETTINGS_SAVE))
        self._save.clicked.connect(lambda _checked=False: self.save())
        self._setup = QPushButton(S.SETTINGS_WIZARD)
        self._setup.clicked.connect(lambda _checked=False: self._open_wizard())
        self._setup_help = QLabel(S.SETTINGS_WIZARD_HELP)
        offered = on_setup_wizard is not None
        self._setup.setVisible(offered)
        self._setup_help.setVisible(offered)
        layout = QVBoxLayout(self)
        layout.addWidget(page_header(S.SETTINGS_TITLE, S.SETTINGS_SUBTITLE))
        layout.addWidget(self._first_run)
        layout.addWidget(self._problem)
        layout.addWidget(field(S.SETTINGS_OWNER, self._owner, S.SETTINGS_OWNER_HELP))
        layout.addWidget(field(S.SETTINGS_HOST, self._host, S.SETTINGS_HOST_HELP))
        layout.addWidget(field(S.SETTINGS_CERT_PIN, self._cert_pin, S.SETTINGS_CERT_PIN_HELP))
        layout.addWidget(field(S.SETTINGS_THEME, self._theme, S.SETTINGS_THEME_HELP))
        layout.addWidget(field(S.SETTINGS_ACCENT, self._accent, S.SETTINGS_ACCENT_HELP))
        layout.addWidget(self._save, alignment=Qt.AlignmentFlag.AlignLeft)
        layout.addWidget(self._status)
        layout.addWidget(QLabel(S.SETTINGS_NO_SECRET))
        layout.addWidget(self._setup, alignment=Qt.AlignmentFlag.AlignLeft)
        layout.addWidget(self._setup_help)
        layout.addWidget(NotifySettingsSection(ctx))
        about_version = QLabel(S.ABOUT_VERSION.format(version=__version__))
        about_version.setObjectName("aboutVersion")
        about_body = QLabel(S.ABOUT_BODY)
        about_body.setWordWrap(True)
        about_body.setObjectName("hint")
        about_donate = QLabel(S.ABOUT_DONATE)
        about_donate.setWordWrap(True)
        about_donate.setObjectName("hint")
        layout.addWidget(section_title(S.ABOUT_TITLE))
        layout.addWidget(about_version)
        layout.addWidget(about_body)
        layout.addWidget(about_donate)
        layout.addStretch(1)
        self._load()

    def _open_wizard(self) -> None:
        if self._on_setup_wizard is not None:
            self._on_setup_wizard()

    def _load(self) -> None:
        try:
            settings = settings_from_document(read_json(self._ctx.settings_path))
        except ProfileError as exc:
            show_problem(self._problem, str(exc))
            return
        if settings is None:
            self._first_run.setVisible(True)
            return
        self._owner.setText(settings.owner_id)
        self._host.setText(settings.host_url)
        self._cert_pin.setText(settings.cert_sha256)
        _select(self._theme, settings.theme)
        _select(self._accent, settings.accent)
        self._first_run.setVisible(False)

    def save(self) -> None:
        theme = str(self._theme.currentData() or "")
        accent = str(self._accent.currentData() or "")
        settings, problems = validate_settings(
            self._owner.text(),
            self._host.text(),
            theme,
            accent,
            self._cert_pin.text(),
        )
        if settings is None:
            show_problem(self._problem, " ".join(problems))
            return
        try:
            write_json(self._ctx.settings_path, settings_to_document(settings))
        except OSError as exc:
            show_problem(self._problem, S.SAVE_FAILED.format(reason=exc.strerror or "disk error"))
            return
        clear_problem(self._problem)
        self._first_run.setVisible(False)
        self._status.setText(S.SETTINGS_SAVED)
        app = QApplication.instance()
        if isinstance(app, QApplication):
            apply_theme(app, settings.theme, settings.accent)


def _choice_box(labels: tuple[str, ...], values: tuple[str, ...]) -> QComboBox:
    box = QComboBox()
    for label, value in zip(labels, values, strict=True):
        box.addItem(label, value)
    return box


def _select(box: QComboBox, value: str) -> None:
    index = box.findData(value)
    if index >= 0:
        box.setCurrentIndex(index)
