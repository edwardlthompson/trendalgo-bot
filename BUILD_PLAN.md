# TrendAlgo Bot — BUILD_PLAN

<!-- remaining-tally -->
**Remaining:** AGENT 0 · LOCAL 0 · CLOUD 0 · AUTO 0 · HUMAN 2 · ADB 0 · **2 open**
<!-- /remaining-tally -->
> **Detail:** [`docs/specs/audit-remediation.md`](docs/specs/audit-remediation.md) · [`docs/CANONICAL_PLAN.md`](docs/CANONICAL_PLAN.md) · **Human gates:** [`docs/HUMAN_BACKLOG.md`](docs/HUMAN_BACKLOG.md) · **Risks:** [`docs/RISK_REGISTER.md`](docs/RISK_REGISTER.md)
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

> Day-to-day device: `.\scripts\packaging\relaunch-device.ps1` (source-first; no PyInstaller).
> **Audit remediation Phases 1–9** archived in COMPLETED_TASKS.md @ `db11ba0`.
> **Market-Context** archived in COMPLETED_TASKS.md @ `db11ba0`.
> Follow-ups: LIVE/NOTIF botd cron wiring; SIM snapshot regen; attorney H-023 post-ELv2.
> Sauce Phase 2–4 backlog: [`docs/specs/secret-sauce-oracle-gap.md`](docs/specs/secret-sauce-oracle-gap.md) — not scheduled.

| Marker | State |
|--------|-------|
| 🔲 | Open |
| ✅ | Done |
| ❌ | Blocked |

### Open HUMAN

- 🔲 [HUMAN] Review Alerts ribbon preview wording (Entered / Left / Trades Windows + Telegram samples); note desired copy in chat or here — then AGENT applies in `strings.py` / `alert_preview.py` / `telegram_format.py` / `scan_alerts.py`
- 🔲 [HUMAN] PF-H1 Optional: mint CoinMarketCal and/or Coindar API keys for live calendar (wizard walks signup; not required for empty-state CI) — see [`docs/HUMAN_BACKLOG.md`](docs/HUMAN_BACKLOG.md)

---

## Open work

### R-Audit-8 — Post product-rec audit

| ID | Task | Owner | Status |
|----|------|-------|--------|
| R-Audit-8.9 | Attorney review of legal packet (F-010 / R-Audit-7.10) | HUMAN | 🔲 |
AGENT 8.1–8.8 + 8.10 ✅ — [`COMPLETED_TASKS.md`](COMPLETED_TASKS.md).

### Carry-forward (HUMAN)

| Track | Owner | Status |
|-------|-------|--------|
| Founder preflights S0–S12 | HUMAN | 🔲 |
| Legal (H-006, H-023) | HUMAN | 🔲 blocks public beta |
| VPS + secrets (H-004, H-008, H-011) | HUMAN | 🔲 |
| Go-live per venue (H-010, H-028) | HUMAN | 🔲 |
| Exchange live worldwide (H-032) | HUMAN | 🔲 |
| DEX live (H-035, H-036) | HUMAN | 🔲 |
Full checklist: [`docs/POST_DELIVERY_PLAN.md`](docs/POST_DELIVERY_PLAN.md) · Local preview: [`docs/LOCAL_DEV.md`](docs/LOCAL_DEV.md)

### Maintenance cadence

| Cadence | Owner | Item |
|---------|-------|------|
| Weekly | AUTO | `check_risk_mitigations.py` · CI/CodeQL on `main` · Dependabot triage |
| Monthly | AUTO | portfolio integrity · production cost · backup dry-run (R-020) |
| Pre-live | AUTO/HUMAN | `go-live-gate.sh --check-only` → `--approve` (H-010/H-028) |
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

| Sprint | Complete | Archive |
|--------|----------|---------|
| Audit remediation P1–P9 | 2026-11-11 | COMPLETED_TASKS.md @ `db11ba0` |
| Market-Context | 2026-11-11 | COMPLETED_TASKS.md @ `db11ba0` |
| Device-Notify-Launch | 2026-10-22 | COMPLETED_TASKS.md @ `49f3987` |
| Oracle-SS | 2026-10-18 | COMPLETED_TASKS.md |
| PF Modular Dashboard | 2026-10-16 | COMPLETED_TASKS.md |
| GP-Template-1.9 | 2026-10-16 | COMPLETED_TASKS.md |
Finished lists: [`COMPLETED_TASKS.md`](COMPLETED_TASKS.md) · Post-delivery: [`docs/POST_DELIVERY_PLAN.md`](docs/POST_DELIVERY_PLAN.md)

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
| UX-008 | Launch: source-first pythonw default; `-Frozen` for packaging | done |
| UX-009 | Market Context dedicated pane on Backtest + Scanner Results | done |
<!-- /ux-inventory -->
