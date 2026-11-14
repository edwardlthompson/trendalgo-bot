# TrendAlgo Bot — BUILD_PLAN

<!-- remaining-tally -->
**Remaining:** AGENT 0 · LOCAL 0 · CLOUD 0 · AUTO 0 · HUMAN 1 · ADB 0 · **1 open**
<!-- /remaining-tally -->
<!-- tally note: TG-ENRICH + NEWS-1 closed this session; HUMAN PF-H1 remains -->
> **Detail:** [`docs/specs/audit-remediation.md`](docs/specs/audit-remediation.md) · [`docs/CANONICAL_PLAN.md`](docs/CANONICAL_PLAN.md) · **Human gates:** [`docs/HUMAN_BACKLOG.md`](docs/HUMAN_BACKLOG.md) · **Risks:** [`docs/RISK_REGISTER.md`](docs/RISK_REGISTER.md)
> **Completed work:** [`COMPLETED_TASKS.md`](COMPLETED_TASKS.md) · **Post-delivery:** [`docs/POST_DELIVERY_PLAN.md`](docs/POST_DELIVERY_PLAN.md) · **Exchange:** [`docs/EXCHANGE_ROADMAP.md`](docs/EXCHANGE_ROADMAP.md) · **DEX:** [`docs/DEX_ROADMAP.md`](docs/DEX_ROADMAP.md)

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
> Follow-ups: LIVE/NOTIF botd cron wiring; SIM snapshot regen; attorney H-023 post-ELv2.

| Marker | State |
|--------|-------|
| 🔲 | Open |
| ✅ | Done |
| ❌ | Blocked |
### Sequential (agent)

| ID | Task | Owner | Status |
|----|------|-------|--------|
| TG-ENRICH | Live enter Telegram: enrich coin with Results OHLC + `alert_trades` before PNG — scope: `telegram_alert_enrich.py`, `scan_alerts.py`, tests | `[AGENT][LOCAL]` | ✅ |
| NEWS-1 | API-key hygiene in security docs (no-withdraw, IP allowlist, no reuse) citing Coinigy breach — scope: `docs/API_ACCESS_LIMITS.md`, `THREAT_MODEL.md`, `SECURITY_TRIAGE.md`, `SETTINGS_KEYS_HELP` | `[AGENT][LOCAL]` | ✅ |
| AUTOSCAN-1 | Autoscan never-dies: re-arm after no-op `_start`, stale/active watchdog, refresh HKCU Run command — scope: `scanner_page.py`, `scanner_schedule.py`, `autostart`/`main_window`, tests | `[AGENT][LOCAL]` | ✅ |
| ALERT-FILTER-1 | Telegram enters only for new pairs in full Qualified-tab filtered set; cold-seed empty previous — scope: `scan_alerts.py`, `scanner_page.py`, `scanner_alert_diff.py`, tests | `[AGENT][LOCAL]` | ✅ |
| ALERT-LEAVE-1 | Exit notify when pair leaves filtered Qualified set; leave reason from board metrics vs floors — scope: `scanner_alert_diff.py`, `scan_alerts.py`, tests | `[AGENT][LOCAL]` | ✅ |
### Open HUMAN

- 🔲 [HUMAN] PF-H1 Optional: mint CoinMarketCal and/or Coindar API keys for live calendar (wizard walks signup; not required for empty-state CI) — see [`docs/HUMAN_BACKLOG.md`](docs/HUMAN_BACKLOG.md)

---

## Open work

### R-Audit-8 — Post product-rec audit

| ID | Task | Owner | Status |
|----|------|-------|--------|
| R-Audit-8.9 | Attorney review of legal packet (F-010 / R-Audit-7.10) | HUMAN | 🔲 |
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

## Completed

Finished BUILD_PLAN rows live in [`COMPLETED_TASKS.md`](COMPLETED_TASKS.md).

<!-- ux-inventory -->
| ID | Change | Status |
|----|--------|--------|
| UX-004 | Settings: danger-styled Remove key + confirm before delete | planned |
| UX-005 | Settings: scroll-to / deep-link section from empty-state CTAs | planned |
<!-- /ux-inventory -->
