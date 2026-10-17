# Feature: crash-inbox

> Disabled GlitchTip/Bugsink stub. Not a live crash-proxy. DPIA before enable.

## Acceptance criteria

- ✅ Example stub ships `enabled: false` with empty DSN/endpoint
- ✅ Gate fails if the stub is enabled or a live DSN is present
- ✅ FOSS path does not depend on Sentry/Crashlytics/GlitchTip/Bugsink SDKs

## Smoke scenario

1. Given this checkout
2. When `scripts/check-crash-inbox.sh` / `agent-run.py check-crash-inbox` runs
3. Then it exits 0 and prints that the stub stays disabled

## Container map

| Layer | Path |
|-------|------|
| Logic | `scripts/lib/crash_inbox.py` |
| View | `docs/CRASH_INBOX.md` |
| Tests | `tests/test_crash_inbox.py` |
| Wiring | `scripts/check-crash-inbox.sh` in validate-bootstrap |
## Tests

- Automated: yes — stub off, DSN rejected
- Verified 2026-10-16: `check-crash-inbox` → Crash inbox stub stays disabled

## Notes

- Local crash queue for operator review is GP-1 (`crash_capture`); this feature is the **remote inbox stub**, kept off
