# Feature: crash-capture

> Opt-in local crash queue. Never auto-sends. Sanitize before persist.

## Acceptance criteria

- ✅ User-visible behavior: after a captured crash, one review dialog; never auto-open GitHub
- ✅ Offline/error behavior: write failure drops the record; handler errors do not re-enter
- ✅ Accessibility: same dialog contract as Feedback
- ✅ i18n: uses `crash_capture.copy` (device; was `feedback.*` on PWA)

## Smoke scenario

1. Given the save-crashes setting is off
2. When an unhandled error occurs
3. Then nothing is persisted
4. When the setting is on, at most one sanitized record is stored; turning the setting off deletes it

## Container map

| Layer | Device (product) | Template stub (ref only) |
|-------|------------------|--------------------------|
| Logic | `src/trendalgo/device/crash_capture/` | `examples/web/src/crash-capture/` |
| Tests | `tests/test_device/test_pending_crash.py` | `pendingCrash.test.ts` |
| Wiring | `app.py` + Settings privacy section ≤10 lines | `appBootstrap.ts` |
## Tests

- Automated: yes — `tests/test_device/test_pending_crash.py`

## Fallback validation

- Why tests are not feasible: N/A (automated tests exist)
- Command: `python3 scripts/agent-run.py feature-gate --stack python`

## Definition of Done

Unit tests for queue-at-most-one, sanitize-before-persist, opt-in false, no re-entry. Fallback: `[HUMAN]` manual throw smoke.

## Notes

- Device: process session + optional `pending_crash.json` when save-crashes is on
- Template web stub used sessionStorage / localStorage; PWA retired (ADR-0016)
- Upload stays opt-in after DPIA (`docs/CRASH_INBOX.md`)
