# Feature: privacy-report

> Shared sanitizer, fingerprint, and markdown builder. No UI and no network.

## Acceptance criteria

- ✅ User-visible behavior: N/A — pure logic only
- ✅ Offline/error behavior: `null`/empty input becomes `""`; size cap drops excess lines (8 KiB / 200 stack lines)
- ✅ Accessibility: N/A
- ✅ i18n: N/A

## Smoke scenario

1. Given a stack containing `C:\Users\Ada\secret.env`, a `ghp_` token, a JWT, and `AKIA`
2. When `sanitize_report_text` and `build_report_markdown` run
3. Then none of those secrets remain and the fingerprint is stable if only the username in a path changes

## Container map

| Layer | Device (product) | Ops / template |
|-------|------------------|----------------|
| Logic | `src/trendalgo/device/privacy_report/` | `scripts/lib/privacy_report_*.py`, template `examples/web/src/privacy-report/` |
| Tests | `tests/test_device/test_privacy_report.py` | `schemas/golden-path/sanitize-fixtures.json` |
| Wiring | none (feedback / crash-capture import this) | |
## Tests

- Automated: yes — `tests/test_device/test_privacy_report.py`

## Fallback validation

- Why tests are not feasible: N/A (automated tests exist)
- Command: `python3 scripts/agent-run.py feature-gate --stack python`

## Definition of Done

See `docs/FEATURE_MODULES.md`. Fallback: `pytest tests/test_device/test_privacy_report.py`.

## Notes

- Run sanitize before persist and again before Copy / Open GitHub
- After each AGENT step: `watch-agent-gates --once --autofix`
