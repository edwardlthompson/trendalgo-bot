"""Settings page: connection, Appearance, Privacy, Data, About — readable form column."""

from __future__ import annotations

import webbrowser
from collections.abc import Callable

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from trendalgo.device import strings as S
from trendalgo.device.about.donations import load_donations, primary_donate_url
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
from trendalgo.device.views.about_updates_section import AboutUpdatesSection
from trendalgo.device.views.collapsible_section import CollapsibleSection
from trendalgo.device.views.crash_privacy_settings import CrashPrivacySection
from trendalgo.device.views.dashboard_modules_settings import DashboardModulesSection
from trendalgo.device.views.exchange_keys_section import ExchangeKeysSection
from trendalgo.device.views.notify_settings import NotifySettingsSection
from trendalgo.device.views.venue_section import VenueSection
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
_FORM_MAX = 560
_EDITOR_MAX = 520


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
        self._use_utc = QCheckBox(S.SETTINGS_USE_UTC)
        self._use_utc.setToolTip(S.SETTINGS_USE_UTC_HELP)
        self._use_utc.setChecked(False)
        for editor in (self._owner, self._host, self._cert_pin, self._theme, self._accent):
            editor.setMaximumWidth(_EDITOR_MAX)
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
        self._setup_help.setObjectName("hint")
        self._setup_help.setWordWrap(True)
        offered = on_setup_wizard is not None
        self._setup.setVisible(offered)
        self._setup_help.setVisible(offered)

        column = QWidget()
        column.setMaximumWidth(_FORM_MAX)
        column.setObjectName("settingsFormColumn")
        col = QVBoxLayout(column)
        col.setContentsMargins(0, 0, 0, 0)
        col.setSpacing(12)
        col.addWidget(page_header(S.SETTINGS_TITLE, S.SETTINGS_SUBTITLE))
        col.addWidget(self._first_run)
        col.addWidget(self._problem)

        connection = CollapsibleSection(S.SETTINGS_CONNECTION, expanded=True)
        connection.setObjectName("settingsSectionConnection")
        connection.add_widget(field(S.SETTINGS_OWNER, self._owner, S.SETTINGS_OWNER_HELP))
        connection.add_widget(field(S.SETTINGS_HOST, self._host, S.SETTINGS_HOST_HELP))
        connection.add_widget(field(S.SETTINGS_CERT_PIN, self._cert_pin, S.SETTINGS_CERT_PIN_HELP))
        col.addWidget(connection)

        keys = CollapsibleSection(S.SETTINGS_KEYS, expanded=False)
        keys.setObjectName("settingsSectionKeys")
        keys.add_widget(ExchangeKeysSection())
        col.addWidget(keys)

        venue = CollapsibleSection(S.SETTINGS_VENUE, expanded=False)
        venue.setObjectName("settingsSectionVenue")
        venue.add_widget(VenueSection(ctx.root))
        col.addWidget(venue)

        appearance = CollapsibleSection(S.SETTINGS_APPEARANCE, expanded=False)
        appearance.setObjectName("settingsSectionAppearance")
        pair = QWidget()
        pair_row = QHBoxLayout(pair)
        pair_row.setContentsMargins(0, 0, 0, 0)
        pair_row.setSpacing(12)
        pair_row.addWidget(field(S.SETTINGS_THEME, self._theme, S.SETTINGS_THEME_HELP), 1)
        pair_row.addWidget(field(S.SETTINGS_ACCENT, self._accent, S.SETTINGS_ACCENT_HELP), 1)
        appearance.add_widget(pair)
        appearance.add_widget(field(S.SETTINGS_USE_UTC, self._use_utc, S.SETTINGS_USE_UTC_HELP))
        col.addWidget(appearance)

        actions = QWidget()
        actions.setObjectName("settingsActions")
        act = QVBoxLayout(actions)
        act.setContentsMargins(0, 4, 0, 4)
        act.setSpacing(8)
        act.addWidget(self._save, alignment=Qt.AlignmentFlag.AlignLeft)
        act.addWidget(self._status)
        act.addWidget(QLabel(S.SETTINGS_NO_SECRET))
        act.addWidget(self._setup, alignment=Qt.AlignmentFlag.AlignLeft)
        act.addWidget(self._setup_help)
        col.addWidget(actions)

        dashboard = CollapsibleSection(S.SETTINGS_DASHBOARD_MODULES, expanded=False)
        dashboard.setObjectName("settingsSectionDashboard")
        dashboard.add_widget(DashboardModulesSection(ctx, on_saved=self._on_module_mins_saved))
        col.addWidget(dashboard)

        privacy_wrap = CollapsibleSection(S.SETTINGS_PRIVACY, expanded=False)
        privacy_wrap.setObjectName("settingsSectionPrivacy")
        privacy_wrap.add_widget(CrashPrivacySection(ctx))
        col.addWidget(privacy_wrap)

        data = CollapsibleSection(S.SETTINGS_DATA, expanded=False)
        data.setObjectName("settingsSectionData")
        data_help = QLabel(DATA_HELP)
        data_help.setObjectName("hint")
        data_help.setWordWrap(True)
        data.add_widget(data_help)
        col.addWidget(data)

        notify_wrap = CollapsibleSection(S.NOTIFY_SECTION, expanded=False)
        notify_wrap.add_widget(NotifySettingsSection(ctx))
        col.addWidget(notify_wrap)

        about = CollapsibleSection(S.ABOUT_TITLE, expanded=False)
        about.setObjectName("settingsSectionAbout")
        about.add_widget(AboutUpdatesSection(ctx))
        about_body = QLabel(S.ABOUT_BODY)
        about_body.setWordWrap(True)
        about_body.setObjectName("hint")
        about_donate = QLabel(S.ABOUT_DONATE)
        about_donate.setWordWrap(True)
        about_donate.setObjectName("hint")
        about.add_widget(about_body)
        about.add_widget(about_donate)
        donations = load_donations()
        venmo = QPushButton(S.ABOUT_VENMO)
        venmo.setMinimumHeight(44)
        venmo.setAccessibleName(S.ABOUT_VENMO)
        donate_url = primary_donate_url(donations)
        venmo.clicked.connect(lambda _c=False, url=donate_url: webbrowser.open(url, new=2))
        about.add_widget(venmo)
        if donations.enabled:
            for link in donations.links:
                if link.url.rstrip("/") == donate_url.rstrip("/"):
                    continue
                about.add_widget(QLabel(f"{link.label}: {link.url}"))
        about.add_widget(AboutFeedbackSection(ctx))
        col.addWidget(about)
        col.addStretch(1)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(column, 0, Qt.AlignmentFlag.AlignTop)
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
        self._use_utc.setChecked(bool(settings.use_utc))
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
            use_utc=bool(self._use_utc.isChecked()),
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
