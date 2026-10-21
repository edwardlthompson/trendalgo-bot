"""Settings page: top action ribbon + drag-and-drop module grid."""

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
from trendalgo.device.portfolio_layout_prefs import Placement
from trendalgo.device.profile import ProfileError, read_json, write_json
from trendalgo.device.settings_layout_prefs import (
    SECTION_IDS,
    SECTION_MINS,
    SettingsLayoutPrefs,
    factory_defaults,
    load_settings_layout,
    save_settings_layout,
)
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
from trendalgo.device.views.crash_privacy_settings import CrashPrivacySection
from trendalgo.device.views.dashboard_modules_settings import DashboardModulesSection
from trendalgo.device.views.exchange_keys_section import ExchangeKeysSection
from trendalgo.device.views.notify_settings import NotifySettingsSection
from trendalgo.device.views.settings_grid_canvas import SettingsGridCanvas
from trendalgo.device.views.telegram_wizard import TelegramWizardDialog
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
_EDITOR_MAX = 520

_SECTION_TITLES: dict[str, str] = {
    "connection": S.SETTINGS_CONNECTION,
    "appearance": S.SETTINGS_APPEARANCE,
    "keys": S.SETTINGS_KEYS,
    "venue": S.SETTINGS_VENUE,
    "dashboard": S.SETTINGS_DASHBOARD_MODULES,
    "privacy": S.SETTINGS_PRIVACY,
    "data": S.SETTINGS_DATA,
    "notify": S.NOTIFY_SECTION,
    "about": S.ABOUT_TITLE,
}


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
        self._status.setObjectName("hint")
        self._save = mark_primary(QPushButton(S.SETTINGS_SAVE))
        self._save.setMinimumHeight(44)
        self._save.setObjectName("settingsRibbonSave")
        self._save.clicked.connect(lambda _checked=False: self.save())
        self._setup = QPushButton(S.SETTINGS_WIZARD)
        self._setup.setMinimumHeight(44)
        self._setup.setObjectName("settingsRibbonSetup")
        self._setup.clicked.connect(lambda _checked=False: self._open_wizard())
        self._setup.setVisible(on_setup_wizard is not None)
        self._telegram = QPushButton(S.NOTIFY_TELEGRAM_WIZARD)
        self._telegram.setMinimumHeight(44)
        self._telegram.setObjectName("settingsRibbonTelegram")
        self._telegram.clicked.connect(lambda _checked=False: self._open_telegram())

        self._edit = QCheckBox(S.SETTINGS_LAYOUT_EDIT)
        self._edit.setToolTip(S.SETTINGS_LAYOUT_EDIT_TIP)
        self._layout_prefs = load_settings_layout(ctx.root)
        self._edit.setChecked(bool(self._layout_prefs.edit_mode))
        self._edit.toggled.connect(self._on_edit_toggled)

        ribbon = QHBoxLayout()
        ribbon.setSpacing(6)
        ribbon.addWidget(self._save, 0, Qt.AlignmentFlag.AlignVCenter)
        ribbon.addWidget(self._setup, 0, Qt.AlignmentFlag.AlignVCenter)
        ribbon.addWidget(self._telegram, 0, Qt.AlignmentFlag.AlignVCenter)
        ribbon.addWidget(self._status, 0, Qt.AlignmentFlag.AlignVCenter)
        ribbon.addStretch(1)

        header = QWidget()
        head = QVBoxLayout(header)
        head.setContentsMargins(0, 0, 0, 0)
        head.setSpacing(6)
        head.addWidget(page_header(S.SETTINGS_TITLE, S.SETTINGS_SUBTITLE))
        head.addWidget(self._first_run)
        head.addWidget(self._problem)
        head.addLayout(ribbon)
        head.addWidget(self._edit)
        no_secret = QLabel(S.SETTINGS_NO_SECRET)
        no_secret.setObjectName("hint")
        no_secret.setWordWrap(True)
        head.addWidget(no_secret)

        self._canvas = SettingsGridCanvas(
            titles=_SECTION_TITLES,
            on_placements_changed=self._on_placements_changed,
        )
        self._canvas.set_grid(self._layout_prefs.grid)
        self._canvas.set_module_mins(SECTION_MINS)
        self._bodies = self._build_section_bodies()
        self._apply_modules()
        self._canvas.set_edit_mode(self._edit.isChecked())

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(header)
        layout.addWidget(self._canvas, 1)
        self._load()

    def _build_section_bodies(self) -> dict[str, QWidget]:
        # Flat card bodies — ModuleChrome owns the title (no nested CollapsibleSection).
        connection, conn_lay = _card_body("settingsSectionConnection")
        conn_lay.addWidget(field(S.SETTINGS_OWNER, self._owner, S.SETTINGS_OWNER_HELP))
        conn_lay.addWidget(field(S.SETTINGS_HOST, self._host, S.SETTINGS_HOST_HELP))
        conn_lay.addWidget(field(S.SETTINGS_CERT_PIN, self._cert_pin, S.SETTINGS_CERT_PIN_HELP))

        appearance, app_lay = _card_body("settingsSectionAppearance")
        pair = QWidget()
        pair_row = QHBoxLayout(pair)
        pair_row.setContentsMargins(0, 0, 0, 0)
        pair_row.setSpacing(12)
        pair_row.addWidget(field(S.SETTINGS_THEME, self._theme, S.SETTINGS_THEME_HELP), 1)
        pair_row.addWidget(field(S.SETTINGS_ACCENT, self._accent, S.SETTINGS_ACCENT_HELP), 1)
        app_lay.addWidget(pair)
        app_lay.addWidget(field(S.SETTINGS_USE_UTC, self._use_utc, S.SETTINGS_USE_UTC_HELP))

        keys, keys_lay = _card_body("settingsSectionKeys")
        keys_lay.addWidget(ExchangeKeysSection())

        venue, venue_lay = _card_body("settingsSectionVenue")
        venue_lay.addWidget(VenueSection(self._ctx.root))

        dashboard, dash_lay = _card_body("settingsSectionDashboard")
        dash_lay.addWidget(
            DashboardModulesSection(
                self._ctx,
                on_saved=self._on_module_mins_saved,
                on_layout_change=self._canvas.schedule_fit_to_content,
            )
        )

        privacy_wrap, priv_lay = _card_body("settingsSectionPrivacy")
        priv_lay.addWidget(CrashPrivacySection(self._ctx))

        data, data_lay = _card_body("settingsSectionData")
        data_help = QLabel(S.SETTINGS_DATA_HELP)
        data_help.setObjectName("hint")
        data_help.setWordWrap(True)
        data_lay.addWidget(data_help)

        notify_wrap, notify_lay = _card_body("settingsSectionNotify")
        notify_lay.addWidget(NotifySettingsSection(self._ctx))

        about, about_lay = _card_body("settingsSectionAbout")
        about_lay.addWidget(AboutUpdatesSection(self._ctx))
        about_body = QLabel(S.ABOUT_BODY)
        about_body.setWordWrap(True)
        about_body.setObjectName("hint")
        about_donate = QLabel(S.ABOUT_DONATE)
        about_donate.setWordWrap(True)
        about_donate.setObjectName("hint")
        about_lay.addWidget(about_body)
        about_lay.addWidget(about_donate)
        donations = load_donations()
        venmo = QPushButton(S.ABOUT_VENMO)
        venmo.setMinimumHeight(44)
        venmo.setAccessibleName(S.ABOUT_VENMO)
        donate_url = primary_donate_url(donations)
        venmo.clicked.connect(lambda _c=False, url=donate_url: webbrowser.open(url, new=2))
        about_lay.addWidget(venmo)
        if donations.enabled:
            for link in donations.links:
                if link.url.rstrip("/") == donate_url.rstrip("/"):
                    continue
                about_lay.addWidget(QLabel(f"{link.label}: {link.url}"))
        about_lay.addWidget(AboutFeedbackSection(self._ctx))

        return {
            "connection": connection,
            "appearance": appearance,
            "keys": keys,
            "venue": venue,
            "dashboard": dashboard,
            "privacy": privacy_wrap,
            "data": data,
            "notify": notify_wrap,
            "about": about,
        }

    def _apply_modules(self) -> None:
        placements = list(self._layout_prefs.placements)
        known = {p.id for p in placements}
        defaults = {p.id: p for p in factory_defaults().placements}
        for sid in SECTION_IDS:
            if sid not in known:
                placements.append(defaults[sid])
        placements = [p for p in placements if p.id in SECTION_IDS]
        self._canvas.set_modules(placements, self._bodies)

    def _on_edit_toggled(self, checked: bool) -> None:
        self._canvas.set_edit_mode(checked)
        self._layout_prefs.edit_mode = bool(checked)
        save_settings_layout(self._ctx.root, self._layout_prefs)

    def _on_placements_changed(self, placements: list[Placement]) -> None:
        self._layout_prefs = SettingsLayoutPrefs(
            grid=self._layout_prefs.grid,
            placements=list(placements),
            layout_version=self._layout_prefs.layout_version,
            edit_mode=self._edit.isChecked(),
        )
        save_settings_layout(self._ctx.root, self._layout_prefs)

    def _open_wizard(self) -> None:
        if self._on_setup_wizard is not None:
            self._on_setup_wizard()

    def _open_telegram(self) -> None:
        TelegramWizardDialog(self._ctx, parent=self).exec()

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


def _card_body(object_name: str) -> tuple[QWidget, QVBoxLayout]:
    """Settings module body: chrome owns the title; keep content tight to the top."""
    host = QWidget()
    host.setObjectName(object_name)
    lay = QVBoxLayout(host)
    lay.setContentsMargins(0, 0, 0, 0)
    lay.setSpacing(10)
    lay.setAlignment(Qt.AlignmentFlag.AlignTop)
    return host, lay


def _choice_box(labels: tuple[str, ...], values: tuple[str, ...]) -> QComboBox:
    box = QComboBox()
    for label, value in zip(labels, values, strict=True):
        box.addItem(label, value)
    return box


def _select(box: QComboBox, value: str) -> None:
    index = box.findData(value)
    if index >= 0:
        box.setCurrentIndex(index)
