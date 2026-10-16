# Linux portable / AppImage launcher design

> **Retired 2026-10-10 (BUILD_PLAN row 23, p7-retire-pwa).** This launcher opened the retired PWA, and `scripts/packaging/launch-linux.sh` is removed. This design is history. The operator path is the device app ([ADR-0016](../adr/0016-headless-bot-local-device.md)).

## User story

Run `./launch-linux.sh` (or AppImage) → API on `127.0.0.1:8000` → browser opens static UI → dry-run Scanner without exchange keys.

## Layout (v1)

Same as Windows portable: repo checkout or extracted zip with `examples/web/dist`, `uv`/`python`, and `scripts/packaging/launch-linux.sh`.

## Process model

Mirror [WINDOWS_LAUNCHER.md](WINDOWS_LAUNCHER.md): health-wait API → `python -m http.server` on dist → `xdg-open` the UI URL → trap EXIT to kill children.

## AppImage (later)

- Asset name: `TrendAlgo-{version}-x86_64.AppImage` (`linux-appimage` format in About).
- Bundle uv-frozen runtime + dist; AppRun invokes `launch-linux.sh` logic.
- No proprietary SDKs; FOSS MIT path only.

### Critique

| Issue | Resolution |
|-------|------------|
| Display-less CI | Script exits non-zero if health fails; skip browser open when `CI=1` |
| Wayland/xdg-open missing | Print URL and continue serving |
