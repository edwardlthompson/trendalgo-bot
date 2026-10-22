# TrendAlgo Bot — BUILD_PLAN

<!-- remaining-tally -->
**Remaining:** AGENT 1 · LOCAL 1 · CLOUD 0 · AUTO 0 · HUMAN 2 · ADB 0 · **3 open**
<!-- /remaining-tally -->
> **Detail:** [`docs/CANONICAL_PLAN.md`](docs/CANONICAL_PLAN.md) · **Human gates:** [`docs/HUMAN_BACKLOG.md`](docs/HUMAN_BACKLOG.md) · **Risks:** [`docs/RISK_REGISTER.md`](docs/RISK_REGISTER.md)
> **Archive:** [`COMPLETED_TASKS.md`](COMPLETED_TASKS.md) · **Post-delivery:** [`docs/POST_DELIVERY_PLAN.md`](docs/POST_DELIVERY_PLAN.md) · **Exchange:** [`docs/EXCHANGE_ROADMAP.md`](docs/EXCHANGE_ROADMAP.md) · **DEX:** [`docs/DEX_ROADMAP.md`](docs/DEX_ROADMAP.md)

### Product (do not drift)

<!-- product-brief-sync:begin -->
> Read `AGENT.md` before any sprint row.

**One-liner:** Photoreal Cycles icons from a locked seed, camera, and lighting.
**Do not drift:** camera, messages, tame, neon

**Rules:**
- Generate store/PWA icons from a JSON manifest (seed, camera, lighting).
- Machine QA only — do not ask a human to review thousands of frames.
- Cycles OptiX is local GPU; CI stays CPU/headless or skip if Blender is missing.
- Do not overwrite live `branding/assets/*.svg` (Sacred vector SoT).

**First milestone:** Seeded icon factory with QA JSON; sample manifest in CI; 4000+ run on This Computer.
<!-- product-brief-sync:end -->

## Now

> **Sprint Device-Notify-Launch** — land uncommitted device UX + source-first relaunch (session 2026-10-21/22). Day-to-day: `.\scripts\packaging\relaunch-device.ps1` (no PyInstaller rebuild).
> Prior **Sprint Sauce-Oracle-Gap** Phases 0–1 ✅; Phase 2–4 backlog in [`docs/specs/secret-sauce-oracle-gap.md`](docs/specs/secret-sauce-oracle-gap.md) — not scheduled.
> Open HUMAN: PF-H1 (optional calendar keys) + alert copy review + carry-forward / R-Audit-8.9.

| Marker | State |
|--------|-------|
| 🔲 | Open |
| ✅ | Done |
| ❌ | Blocked |
### Sequential — Device notify + source-first launch

- ✅ [AGENT][LOCAL] MSI registries + null-safe scanner filter load + frozen config path — scope: `scripts/packaging/build-windows-desktop.ps1`, `src/trendalgo/bundled_config.py`, `src/trendalgo/exchanges/registry.py`, `src/trendalgo/venues/registry.py`, `src/trendalgo/device/views/scanner_filters.py`, `src/trendalgo/device/selftest.py`, `tests/test_device/test_device_scan_page.py`
- ✅ [AGENT][LOCAL] Telegram BotFather copy-script wizard + Detect deleteWebhook→getUpdates — scope: `src/trendalgo/device/views/telegram_wizard.py`, `src/trendalgo/device/views/copy_snippet.py`, `src/trendalgo/device/telegram_botfather.py`, `src/trendalgo/notifications/telegram.py`, `src/trendalgo/device/strings.py`, `tests/test_device/test_telegram_wizard.py`, `tests/test_telegram.py`
- ✅ [AGENT][LOCAL] Alerts notify ribbon (Entered/Left/Trades master toggles + preview + Test Windows/Telegram) — scope: `src/trendalgo/device/alert_preview.py`, `src/trendalgo/device/views/alerts_notify_ribbon.py`, `src/trendalgo/device/views/alerts_page.py`, `src/trendalgo/device/views/main_window.py`, `src/trendalgo/device/scan_alerts.py`, `tests/test_device/test_alert_preview.py`, `tests/test_device/test_alerts_notify_ribbon.py`
- ✅ [AGENT][LOCAL] Source-first launch default + `-Frozen` + `relaunch-device.ps1` + docs/rule — scope: `scripts/packaging/launch-device.ps1`, `scripts/packaging/relaunch-device.ps1`, `scripts/lib/device_launch_prefer.py`, `.cursor/rules/device-no-console.mdc`, `docs/packaging/WINDOWS_LAUNCHER.md`, `docs/LOCAL_DEV.md`, `tests/test_scripts/test_device_launch_prefer.py`
- ✅ [AGENT][LOCAL] Finish source-first gates — `watch-agent-gates --once --autofix --scope auto` green; smoke `relaunch-device.ps1` — scope: `scripts/packaging/`, `tests/test_scripts/test_device_launch_prefer.py`
- ✅ [AGENT][LOCAL] Commit + Conventional Commits for Device-Notify-Launch tree (explicit paths only; no `.cursor/*.txt` noise) — scope: listed files above + `src/trendalgo/bundled_config.py`
- 🔲 [HUMAN] Review Alerts ribbon preview wording (Entered / Left / Trades Windows + Telegram samples); note desired copy in chat or BUILD_PLAN
- ❌ [AGENT][LOCAL] Apply alert title/body copy from HUMAN notes — blocked until HUMAN preview review — scope: `src/trendalgo/device/strings.py`, `src/trendalgo/device/alert_preview.py`, `src/trendalgo/notifications/telegram_format.py`, `src/trendalgo/device/scan_alerts.py`
- ✅ [AGENT][LOCAL] Next MSI/ship: registries already in `--add-data`; verify frozen selftest `registries` OK on release build — scope: `scripts/packaging/build-windows-desktop.ps1`, `src/trendalgo/device/selftest.py`
- 🔲 [HUMAN] PF-H1 Optional: mint CoinMarketCal and/or Coindar API keys for live calendar (wizard walks signup; not required for empty-state CI) — see [`docs/HUMAN_BACKLOG.md`](docs/HUMAN_BACKLOG.md)

> **R-BA-17** / template FOSS surface archived in COMPLETED_TASKS. Alignment: [`docs/BOOTSTRAP_ALIGNMENT.md`](docs/BOOTSTRAP_ALIGNMENT.md) (`upstream_aligned_version` 1.10.0). Skills: [`docs/SKILLS_RECIPES.md`](docs/SKILLS_RECIPES.md).

---

## Open work

### R-Audit-8 — Post product-rec audit (2026-07-12)

AGENT 8.1–8.8 ✅ (see [`COMPLETED_TASKS.md`](COMPLETED_TASKS.md)). Remaining:

| ID | Task | Owner | Status |
|----|------|-------|--------|
| R-Audit-8.9 | Attorney review of legal packet (F-010 / R-Audit-7.10) | HUMAN | 🔲 |
| R-Audit-8.10 | Triage PR #13 release + PR #12 web deps after CI green (F-011) | AGENT | ✅ |
### Carry-forward (HUMAN)

| Track | Owner | Status |
|-------|-------|--------|
| Founder preflights S0–S12 | HUMAN | 🔲 |
| Legal (H-006, H-023) | HUMAN | 🔲 blocks public beta |
| VPS + secrets (H-004, H-008, H-011) | HUMAN | 🔲 |
| Go-live per venue (H-010, H-028) | HUMAN | 🔲 |
| Exchange live worldwide (H-032) | HUMAN | 🔲 |
| DEX live (H-035, H-036) | HUMAN | 🔲 |
| CI green + v0.4.x tag | AGENT/HUMAN | ✅ v0.4.1 tagged 2026-07-12 |
| Risk Register Zero | AUTO | ✅ |
| Scope preflights H-013–H-025 | AGENT | ✅ |
Founder gates, VPS, legal, go-live, and recurring controls — full checklist: [`docs/POST_DELIVERY_PLAN.md`](docs/POST_DELIVERY_PLAN.md).

### Maintenance cadence

| Cadence | Owner | Item |
|---------|-------|------|
| Weekly | AUTO | `check_risk_mitigations.py` · CI/CodeQL on `main` · Dependabot triage |
| Monthly | AUTO | portfolio integrity · production cost · backup dry-run (R-020) |
| Pre-live | AUTO/HUMAN | `go-live-gate.sh --check-only` → `--approve` (H-010/H-028) |
Local preview (S13+ UI/API): [`docs/LOCAL_DEV.md`](docs/LOCAL_DEV.md) · `scripts/dev-local.ps1`

Founder gate CLI: [`docs/FOUNDER_GATES.md`](docs/FOUNDER_GATES.md) · `python scripts/founder_gate.py status`

---

## Owner labels

| Label | Owner |
|-------|-------|
| `AGENT` | Code, docs, tests |
| `HUMAN` | Credentials, legal, go-live |
| `AUTO` | CI / gate scripts |
**Hard gates (never AUTO):** H-006, H-008, H-010, H-011, H-023, H-028, H-031, H-032, H-036

---

## Archived sprints

Finished sprint task lists: [`COMPLETED_TASKS.md`](COMPLETED_TASKS.md). Post-delivery checklist: [`docs/POST_DELIVERY_PLAN.md`](docs/POST_DELIVERY_PLAN.md).

<!-- ux-inventory -->
| ID | Change | Status |
|----|--------|--------|
| UX-001 | Settings Exchange keys: tall Query/Trade + Exchange combo popups (no clipped rows) | done |
| UX-002 | Settings Exchange keys: visible Public API key / Private API secret labels + help | done |
| UX-003 | Settings IA: Connection → Appearance → Save → Keys (expanded) → Venue → rest; keys save copy | done |
| UX-004 | Settings: danger-styled Remove key + confirm before delete | planned |
| UX-005 | Settings: scroll-to / deep-link section from empty-state CTAs | planned |
| UX-006 | Alerts ribbon: Entered/Left/Trades master notify + preview + Test Win/TG | done |
| UX-007 | Telegram wizard: BotFather copy boxes + deleteWebhook Detect | done |
| UX-008 | Launch: source-first pythonw default; `-Frozen` for packaging | done (gates row open) |
<!-- /ux-inventory -->
