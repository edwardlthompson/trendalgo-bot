# ADR-0015 — Desktop shell (pywebview + WebView2)

- **Status:** Retired 2026-10-10 (BUILD_PLAN row 23, p7-retire-pwa); superseded by ADR-0016. The pywebview shell and the PWA it hosted are removed.
- **Date:** 2026-10-08
- **Relates to:** ADR-0012 (grandma), ADR-0014 (local Windows launcher)
- **Deciders:** Operator product path

## Context

ADR-0014 opened the default browser against a same-origin API. Operators want an **installable Windows program** that shows the UI in a **native window** (no separate Chrome/Edge window), while keeping the existing Vite PWA and FastAPI stack.

## Decision

1. **Operator Windows default:** `trendalgo-desktop` — [pywebview](https://pywebview.flowrl.com/) (WebView2 on Windows) loads `http://127.0.0.1:8000/` after spawning `trendalgo.api.main` with `TRENDALGO_SERVE_WEB=1`.
2. **Browser / PWA path** (`launch-windows.ps1`, Vite preview) remains a **developer fallback**.
3. **Hosted grandma URL** (ADR-0012) is unchanged for sharing without install.
4. **Still defer** Electron/Tauri unless WebView2 proves insufficient; signed NSIS/winget stay later (About `win-setup` name reserved).

## Alternatives considered

| Option | Why not now |
|--------|-------------|
| Electron / Tauri | Heavier; proprietary friction vs FOSS MIT path |
| Pure WinUI rewrite | Rewrites Scanner/LTS HTML |
| Browser-only (ADR-0014 alone) | Opens a separate browser app |

## Consequences

- Dependency: optional extra `desktop` (`pywebview`); WebView2 Runtime usually preinstalled on Win10/11.
- Packaging: [`scripts/packaging/build-windows-desktop.ps1`](../../scripts/packaging/build-windows-desktop.ps1); shortcuts target the desktop entry.
- Docs: [`FIRST_RUN_USER`](../help/FIRST_RUN_USER.md), [`WINDOWS_LAUNCHER`](../packaging/WINDOWS_LAUNCHER.md).
- **OS notifications (default on):** Windows WebView2 `PermissionRequested` allows Notifications; UI loads with `?desktop=1` so Scanner Tier-A alerts enable by default (opt-out persists as `0`). Linux/macOS use the same JS default; host hooks follow as those shells ship.

### Critique

| Issue | Resolution |
|-------|------------|
| “No browser” vs WebView2 | Native OS window + embedded engine; does not open Chrome/Edge UI |
| API race before window | Health poll before `webview.start` |
| Filters reset each launch | `webview.start(private_mode=False, storage_path=data/launcher/webview)` + server `scanner_host_filters.json` |
| ADR-0014 conflict | Amended: browser launcher is fallback; desktop is product default |
| WebView2 denies notifications by default | Host allows Notifications; sticky profile permission for app origin |
| Linux/mac | Same JS default-on; native host hooks when those desktop entries ship |
