# Feature: Opportunity Scanner (LTS absorption)

> Sprint 4.5 · Feature IDs O1–O15, NT2, U5

## Acceptance criteria

- ✅ User-visible behavior: PWA Scanner tab shows ranked opportunities with sparklines, uniformity, gain; run scan + pin watchlist
- ✅ Offline/error behavior: empty state when no snapshot; API offline shows shell status message
- ✅ Accessibility: scanner table headers, nav buttons with aria labels; sparklines `aria-hidden`
- ✅ i18n: keys under `scanner.*` in `examples/web/src/locales/en.json`

## Smoke scenario

1. Given API is running (`uv run trendalgo-api`)
2. When user opens Scanner tab and clicks Run scan
3. Then ranked table appears with at least one opportunity and no console errors

## Container map

| Layer | Path |
|-------|------|
| Logic | `src/trendalgo/scanner/` |
| API | `src/trendalgo/api/routes/scanner.py` |
| View | `examples/web/src/scanner/ScannerPanel.ts` |
| Tests | `tests/test_scanner/` |
| Wiring | `api/app.py` router + lifespan scheduler |

## Definition of Done

- `bash scripts/lts-parity-check.sh` exit 0
- `bash scripts/check_scanner_imports.sh` exit 0
- Scanner tests in CI; coverage includes `scanner/*`
- H-014 human approval before standalone repo archive (not AUTO)

## Notes

- Native port — see `docs/LTS_ABSORPTION.md` and `vendor_manifest.json`
- Strong Uptrend Scanner template: `strong-uptrend-scanner` in `templates/registry.py`
