"""Settings page: connection, then Appearance → Dashboard → Privacy → Data → About."""

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
from trendalgo.device.about.donations import load_donations
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
from trendalgo.device.views.about_feedback_section import AboutFeedbackSection
from trendalgo.device.views.collapsible_section import CollapsibleSection
from trendalgo.device.views.crash_privacy_settings import CrashPrivacySection
from trendalgo.device.views.dashboard_modules_settings import DashboardModulesSection
from trendalgo.device.views.notify_settings import NotifySettingsSection
from trendalgo.device.views.widgets import (
    clear_problem,
    field,
    mark_primary,
    page_header,
    problem_label,
    show_problem,
)

THEME_LABELS = (S.THEME_SYSTEM, S.THEME_LIGHT, S.THEME_DARK)
ACCENT_LABELS = (S.ACCENT_DEFAULT, *S.ACCENT_NAMES)
DATA_HELP = (
    "Export plans, journal CSV, and scan snapshots from the Export page. "
    "Settings stay on this PC in settings.json."
)


class SettingsPage(QWidget):
    def __init__(
        self,
        ctx: DeviceContext,
        on_setup_wizard: Callable[[], None] | None = None,
        *,
        on_module_mins_saved: Callable[[], None] | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._ctx = ctx
        self._on_setup_wizard = on_setup_wizard
        self._on_module_mins_saved = on_module_mins_saved
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
        self._save.setMinimumHeight(44)
        self._save.clicked.connect(lambda _checked=False: self.save())
        self._setup = QPushButton(S.SETTINGS_WIZARD)
        self._setup.setMinimumHeight(44)
        self._setup.clicked.connect(lambda _checked=False: self._open_wizard())
        self._setup_help = QLabel(S.SETTINGS_WIZARD_HELP)
        offered = on_setup_wizard is not None
        self._setup.setVisible(offered)
        self._setup_help.setVisible(offered)

        layout = QVBoxLayout(self)
        layout.addWidget(page_header(S.SETTINGS_TITLE, S.SETTINGS_SUBTITLE))
        layout.addWidget(self._first_run)
        layout.addWidget(self._problem)

        connection = CollapsibleSection(S.SETTINGS_CONNECTION, expanded=True)
        connection.setObjectName("settingsSectionConnection")
        connection.add_widget(field(S.SETTINGS_OWNER, self._owner, S.SETTINGS_OWNER_HELP))
        connection.add_widget(field(S.SETTINGS_HOST, self._host, S.SETTINGS_HOST_HELP))
        connection.add_widget(field(S.SETTINGS_CERT_PIN, self._cert_pin, S.SETTINGS_CERT_PIN_HELP))
        layout.addWidget(connection)

        appearance = CollapsibleSection(S.SETTINGS_APPEARANCE, expanded=True)
        appearance.setObjectName("settingsSectionAppearance")
        appearance.add_widget(field(S.SETTINGS_THEME, self._theme, S.SETTINGS_THEME_HELP))
        appearance.add_widget(field(S.SETTINGS_ACCENT, self._accent, S.SETTINGS_ACCENT_HELP))
        layout.addWidget(appearance)

        layout.addWidget(self._save, alignment=Qt.AlignmentFlag.AlignLeft)
        layout.addWidget(self._status)
        layout.addWidget(QLabel(S.SETTINGS_NO_SECRET))
        layout.addWidget(self._setup, alignment=Qt.AlignmentFlag.AlignLeft)
        layout.addWidget(self._setup_help)

        dashboard = CollapsibleSection(S.SETTINGS_DASHBOARD_MODULES, expanded=False)
        dashboard.setObjectName("settingsSectionDashboard")
        dashboard.add_widget(DashboardModulesSection(ctx, on_saved=self._on_module_mins_saved))
        layout.addWidget(dashboard)

        privacy_wrap = CollapsibleSection("Privacy", expanded=False)
        privacy_wrap.setObjectName("settingsSectionPrivacy")
        privacy_wrap.add_widget(CrashPrivacySection(ctx))
        layout.addWidget(privacy_wrap)

        data = CollapsibleSection(S.SETTINGS_DATA, expanded=False)
        data.setObjectName("settingsSectionData")
        data_help = QLabel(DATA_HELP)
        data_help.setObjectName("hint")
        data_help.setWordWrap(True)
        data.add_widget(data_help)
        layout.addWidget(data)

        notify_wrap = CollapsibleSection(S.NOTIFY_SECTION, expanded=False)
        notify_wrap.add_widget(NotifySettingsSection(ctx))
        layout.addWidget(notify_wrap)

        about = CollapsibleSection(S.ABOUT_TITLE, expanded=False)
        about.setObjectName("settingsSectionAbout")
        about_version = QLabel(S.ABOUT_VERSION.format(version=__version__))
        about_version.setObjectName("aboutVersion")
        about_body = QLabel(S.ABOUT_BODY)
        about_body.setWordWrap(True)
        about_body.setObjectName("hint")
        about_donate = QLabel(S.ABOUT_DONATE)
        about_donate.setWordWrap(True)
        about_donate.setObjectName("hint")
        about.add_widget(about_version)
        about.add_widget(about_body)
        about.add_widget(about_donate)
        donations = load_donations()
        if donations.enabled:
            for link in donations.links:
                about.add_widget(QLabel(f"{link.label}: {link.url}"))
        about.add_widget(AboutFeedbackSection(ctx))
        layout.addWidget(about)
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
