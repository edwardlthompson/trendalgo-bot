# Feature: feedback

> About / Help review dialogs for bug and feature reports. Not a donate nag.

## Acceptance criteria

- ✅ User-visible behavior: About has Report a bug and Request a feature; review panel shows escaped preview, Copy, Open GitHub, Discard
- ✅ Offline/error behavior: Copy still works; Open GitHub disabled with i18n reason; search fail-soft
- ✅ Accessibility: dialog labelled buttons; no Android Toast
- ✅ i18n: `feedback.copy` (device; was `feedback.*` on PWA)

## Smoke scenario

1. Given crash-capture is off
2. When the user opens Settings → About and chooses Report a bug, types a description
3. Then they can copy sanitized markdown; Open GitHub is enabled only when description or stack exists **and** a release repo is configured (GP-3)

## Container map

| Layer | Device (product) | Template stub (ref only) |
|-------|------------------|--------------------------|
| View | `src/trendalgo/device/views/feedback_dialog.py` | `FeedbackPanel.ts` |
| Logic | `src/trendalgo/device/feedback/` | `examples/web/src/feedback/` |
| Tests | `tests/test_device/test_feedback_preview.py` | `preview.test.ts` |
| Wiring | Settings About section ≤10 lines | `AppShell.ts` |
## Tests

- Automated: yes — `tests/test_device/test_feedback_preview.py`

## Fallback validation

- Why tests are not feasible: N/A (automated tests exist)
- Command: `python3 scripts/agent-run.py feature-gate --stack python`

## Definition of Done

See `docs/FEATURE_MODULES.md`. XSS test: preview never uses rich HTML of reporter text (plain `QPlainTextEdit`).

## Notes

- Settings toggle “Save crash details for me to review” defaults off (`crash_prefs.json`; GP-1)
- Discard best-effort clears clipboard text we wrote
- Open GitHub body URL lands in GP-3
