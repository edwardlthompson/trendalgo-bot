# Windows desktop shell + launcher

> **Retired 2026-10-10 (BUILD_PLAN row 23, p7-retire-pwa).** The pywebview shell (`src/trendalgo/desktop/`) and `scripts/packaging/launch-windows.ps1` are removed.
>
> **Device GUI (current):** `.\scripts\packaging\launch-device.ps1` — no console. Frozen build: `.\scripts\packaging\build-windows-desktop.ps1 -Device` ([ADR-0016](../adr/0016-headless-bot-local-device.md)). Do **not** use `uv run python -m trendalgo.device` for normal GUI runs (that attaches a console; closing it kills the app). Testing only: `-KeepConsole` or `TRENDALGO_KEEP_CONSOLE=1`.
>
> The sections below are history.

## User story

Double-click **TrendAlgo** → API starts on `127.0.0.1:8000` (dry-run) with `TRENDALGO_SERVE_WEB=1` → **native pywebview (WebView2) window** shows the UI — no separate Chrome/Edge window.

ADR: [0015-desktop-shell-pywebview](../adr/0015-desktop-shell-pywebview.md) (amends ADR-0014 operator default).

## Product default: desktop entry

```powershell
.\scripts\packaging\build-windows-desktop.ps1              # build PWA + sync deps
.\scripts\packaging\build-windows-desktop.ps1 -ShortcutsOnly   # Desktop + Start Menu (no console)
# Debug with console:
uv run --extra desktop trendalgo-desktop-console

```

Desktop shortcut runs `launch-windows-desktop.vbs` (hidden console) and uses `branding/assets/app-icon.ico`.

Requires **WebView2 Runtime** (preinstalled on most Win10/11 PCs).

**Notifications:** enabled by default (Windows toast via WebView2). Scanner → “Update alerts on”. Turn off in the LTS notify control to opt out.

## Layout

```
TrendAlgo/
  scripts/packaging/build-windows-desktop.ps1
  scripts/packaging/launch-windows.ps1   # browser fallback
  examples/web/dist/
  data/launcher/                         # TRENDALGO_DATA_DIR
  .env.example → .env

```

## Process model (desktop)

1. Ensure `.env` / `TRENDALGO_DATA_DIR` / dry-run / `TRENDALGO_SERVE_WEB=1`.
2. Restore coin icons when available; require `examples/web/dist`.
3. Spawn API (`uv run python -m trendalgo.api.main`).
4. Poll `GET /api/v1/health`.
5. `webview.create_window("TrendAlgo", http://127.0.0.1:8000/)`.
6. On window close: terminate API child.

## Browser fallback (developers)

[`launch-windows.ps1`](../../scripts/packaging/launch-windows.ps1) still starts the API and opens the default browser. Prefer `trendalgo-desktop` for operators.

## Install (Desktop + Start Menu + optional MSI)

```powershell
.\scripts\packaging\install-windows-desktop.ps1          # Desktop + Start Menu\TrendAlgo + Apps list
.\scripts\packaging\install-windows-desktop.ps1 -Msi     # also build dist\windows-msi\TrendAlgo-*-x64.msi (needs wix)
.\scripts\packaging\install-windows-desktop.ps1 -Uninstall

```

Installs a silent launcher under `%LOCALAPPDATA%\Programs\TrendAlgo\` (points at this repo). Search Start for **TrendAlgo**.

## NSIS / setup.exe (later)

- Full bundled setup.exe (PyInstaller one-folder) remains optional for offline machines.

## Non-goals (v1)

- Electron/Tauri (unless WebView2 blocked)
- Code signing / winget
- Live trading defaults
- Linux/mac desktop (can follow via pywebview)

### Critique

| Issue | Resolution |
|-------|------------|
| Node required for first build | `build-windows-desktop.ps1` builds once |
| API race before UI | Health poll before webview |
| “No browser” vs WebView2 | Native window + embedded engine |
| Secrets in zip | Only `.env.example`; never ship live keys |
