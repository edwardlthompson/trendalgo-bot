# ADR-0014 — Local Windows first for operator testing

- **Status:** Accepted; amended by ADR-0016. The browser launcher it describes was retired on 2026-10-10 (BUILD_PLAN row 23, p7-retire-pwa).
- **Date:** 2026-10-08
- **Relates to:** ADR-0012 (grandma distribution), ADR-0013 (LTS vendor)

## Context

Operator testing on a home PC felt slow when using the browser PWA against a local or remote stack. Cloud always-on hosting remains a large technical step. Heavy Scanner / LTS backtest work already runs in the Python API on whichever host serves `:8000`.

## Decision

1. **Primary path for operator / home testing (amended by ADR-0015):** Windows **desktop shell** (`trendalgo-desktop` / pywebview). Browser launcher ([`launch-windows.ps1`](../../scripts/packaging/launch-windows.ps1)) remains a developer fallback — API + built PWA on `127.0.0.1`, dry-run default.
2. **One origin:** with `TRENDALGO_SERVE_WEB=1`, FastAPI serves `examples/web/dist` (including `/lts-dashboard`) from the same port as the API.
3. **Hosted dry-run URL** (ADR-0012 grandma primary) remains the path for sharing with others once a HUMAN provisions VPS — secondary until that URL exists.
4. **Still defer** Electron/Tauri, signed NSIS, and winget (unless WebView2 is insufficient — see ADR-0015).

## Consequences

- [`docs/help/FIRST_RUN_USER.md`](../help/FIRST_RUN_USER.md) leads with the Windows launcher.
- LTS coin icon bulk is optional (remote/monogram fallbacks) so first paint is not blocked by thousands of PNGs.
- Production live trading remains VPS-only (ADR-0002); launcher stays dry-run.
