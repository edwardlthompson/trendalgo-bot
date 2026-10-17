# Feature: settings-chrome

> Minimal home chrome and glanceable Settings/About menus for Golden Path (M49).

## Acceptance criteria

- ✅ Home header has brand + host badge only (no theme / About / donate)
- ✅ Theme lives under Settings → Appearance (system / light / dark)
- ✅ Settings Golden Path groups: Appearance → Privacy → Data → About (device host fields sit above)
- ✅ About: App → donate → Feedback dropdown
- ✅ Offline: menus render from local state; no network required
- ✅ Accessibility: Settings nav labeled; dropdowns labeled; primary actions ≥ 44px
- ✅ i18n: device strings / feedback.copy

## Smoke scenario

1. Given the device main window
2. When the user opens Settings, changes theme via the dropdown, then scrolls to About
3. Then the header never showed theme/About/donate; About lists version and donate; Feedback is a dropdown

## Container map

| Layer | Device (product) | Template stub (ref only) |
|-------|------------------|--------------------------|
| Logic | `src/trendalgo/device/settings_chrome.py` | `examples/web/src/settings/sectionOrder.ts` |
| View | `views/chrome.py`, `views/settings_page.py` | `AppShell.ts`, `SettingsPanel.ts` |
| Tests | `tests/test_device/test_settings_chrome.py` | `AppShell.test.ts` |
## Tests

- Automated: yes — `tests/test_device/test_settings_chrome.py`
- Gate: `check-tour-coach-chrome` (already green)

## Fallback validation

- Command: `python3 scripts/agent-run.py watch-agent-gates --once --autofix --scope auto`

## Notes

- Contract: `docs/DESIGN_GUIDE.md` Chrome and menus; ADR `docs/adr/0004-settings-chrome.md`
- Device host/owner fields are ADR-0016; they sit above the Golden Path section order
