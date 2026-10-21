# Packaging — local one-click launcher

> **Device app (current):** build with `.\scripts\packaging\build-windows-desktop.ps1 -Device`, then install Start Menu / Desktop / taskbar shortcuts with `.\scripts\packaging\install-windows-device.ps1` ([ADR-0016](../adr/0016-headless-bot-local-device.md)). Use `-SkipBuild` when `dist\windows-device\TrendAlgoDevice\TrendAlgoDevice.exe` is already current.
>
> **Release installers (MSI + setup.exe):** requires [WiX 5.x](https://wixtoolset.org/) (`dotnet tool install -g wix --version 5.0.2`). Then:
>
> ```powershell
> .\scripts\packaging\build-windows-msi.ps1          # or -BuildDevice to freeze first
> # outputs: dist\windows-msi\TrendAlgo-X.Y.Z-x64.msi
> #          dist\windows-msi\TrendAlgo-X.Y.Z-x64-setup.exe
> ```
>
> GitHub Release job `windows-device-installers` (in `release.yml`) uploads those assets on publish / `workflow_dispatch`. Assets are **unsigned** (SmartScreen may warn) until HUMAN code signing. Do not use WiX 7+ here (OSMF EULA).
>
> **Retired 2026-10-10 (BUILD_PLAN row 23, p7-retire-pwa).** The browser and pywebview launchers are removed. The rest of this page is history.

> ADR: [`0015`](../adr/0015-desktop-shell-pywebview.md) · [`0014`](../adr/0014-local-windows-first.md) · [`0012`](../adr/0012-grandma-distribution.md) · User: [`FIRST_RUN_USER`](../help/FIRST_RUN_USER.md)

## Host TLS for botd (device pin)

Generate a self-signed cert for Docker `:8443` and print the SHA-256 pin for device Settings:

```powershell
.\scripts\packaging\gen-botd-tls.ps1 -OutDir .\docker\secrets
```

Mount `botd.crt` / `botd.key` per `docker/Dockerfile.bot`. Paste the pin into Settings (`cert_sha256`) before **Send to host**. Pin `docker/botd-release.json` image SHA before install (null refuses install).

**Usability test (HUMAN row 20):** exercise list in [`docs/help/FIRST_RUN_USER.md`](../help/FIRST_RUN_USER.md); a11y/visual smoke in [`docs/DEVICE_PARITY_LIST.md`](../DEVICE_PARITY_LIST.md) §13.

---

**Goal:** double-click **TrendAlgo** → native desktop window (pywebview/WebView2) + dry-run API on a home PC. Hosted grandma URL remains optional until a VPS link exists.

| Platform | Design | Prototype |
|----------|--------|-----------|
| Windows desktop | [WINDOWS_LAUNCHER.md](WINDOWS_LAUNCHER.md) | [`build-windows-desktop.ps1`](../../scripts/packaging/build-windows-desktop.ps1) · `uv run --extra desktop trendalgo-desktop` |
| Windows browser fallback | same | [`launch-windows.ps1`](../../scripts/packaging/launch-windows.ps1) |
| Linux | [LINUX_LAUNCHER.md](LINUX_LAUNCHER.md) | [`launch-linux.sh`](../../scripts/packaging/launch-linux.sh) |

**Windows quick start:**

```powershell
.\scripts\packaging\build-windows-desktop.ps1 -SkipBuild
uv run --extra desktop trendalgo-desktop
```

Native window on `http://127.0.0.1:8000/` (`TRENDALGO_SERVE_WEB=1`). Browser fallback: `launch-windows.ps1`.

**Coin icons (optional):** [`restore-lts-coin-icons.ps1`](../../scripts/packaging/restore-lts-coin-icons.ps1) soft-fails when no pack is present (PNGs under `examples/web/public/lts-dashboard/icons/coins` are gitignored). Set `TRENDALGO_LTS_ICONS_SRC` to seed a local folder of `*.png`; otherwise the Scan dashboard uses CDN + monogram fallbacks. Slim mode: [`slim-lts-icons.ps1`](../../scripts/packaging/slim-lts-icons.ps1).

**Release asset names** (About update checker / `select_product_asset`):

| Format | GitHub Release asset pattern |
|--------|------------------------------|
| `win-setup` | `TrendAlgo-X.Y.Z-x64-setup.exe` (Burn; primary for `kind=exe`) |
| `win-msi` | `TrendAlgo-X.Y.Z-x64.msi` |
| `linux-appimage` | `TrendAlgo-X.Y.Z-x86_64.AppImage` (not built yet) |
| `pwa` | (browser / Vite preview — no desktop asset) |

Code signing and winget submission stay deferred ([ADR-0012](../adr/0012-grandma-distribution.md)); unsigned MSI/setup ship from CI.
