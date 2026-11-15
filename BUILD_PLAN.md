# TrendAlgo Bot — BUILD_PLAN

<!-- remaining-tally -->
**Remaining:** AGENT 1 · LOCAL 0 · CLOUD 1 · AUTO 0 · HUMAN 18 · ADB 0 · **19 open** (HUMAN pack + DEX-P4b Cloud)
<!-- /remaining-tally -->
<!-- tally note: Multi-venue Sequential archived 2026-11-15 -->
> **Detail:** [`docs/specs/audit-remediation.md`](docs/specs/audit-remediation.md) · [`docs/CANONICAL_PLAN.md`](docs/CANONICAL_PLAN.md) · **Human gates:** [`docs/HUMAN_BACKLOG.md`](docs/HUMAN_BACKLOG.md) · **Risks:** [`docs/RISK_REGISTER.md`](docs/RISK_REGISTER.md)
> **Completed work:** [`COMPLETED_TASKS.md`](COMPLETED_TASKS.md) · **Post-delivery:** [`docs/POST_DELIVERY_PLAN.md`](docs/POST_DELIVERY_PLAN.md) · **Exchange:** [`docs/EXCHANGE_ROADMAP.md`](docs/EXCHANGE_ROADMAP.md) · **DEX:** [`docs/DEX_ROADMAP.md`](docs/DEX_ROADMAP.md) · **Support:** [`docs/SUPPORT_MATRIX.md`](docs/SUPPORT_MATRIX.md)
> **Sauce / Market Context / logos** archived in COMPLETED_TASKS.md @ `665d6f5` · v1.15.2.
> **Multi-venue Sequential (CEX/DEX/TF)** archived in COMPLETED_TASKS.md (2026-11-15).
> **Honesty DoD (every multi-venue AGENT row):** bump [`support_matrix.json`](src/trendalgo/device/data/support_matrix.json) + [`docs/SUPPORT_MATRIX.md`](docs/SUPPORT_MATRIX.md) + README Exchange / today / coming-soon + `about_line` when capability changes; scoped `test_support_matrix.py` green.

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

> **Multi-venue Sequential (CEX/DEX/TF)** + TF-P2…P4 archived in COMPLETED_TASKS.md (2026-11-15). LOCAL lane clear; remaining AGENT is DEX-P4b `[CLOUD]`.

### Human work (complete in this order)

> Single pack for all founder actions. Soft/optional first only when it unblocks nothing critical — **legal → ops → secrets → live → expand**. Detail + approve CLI: [`docs/HUMAN_BACKLOG.md`](docs/HUMAN_BACKLOG.md) · [`docs/FOUNDER_GATES.md`](docs/FOUNDER_GATES.md). Hard gates never AUTO.

| # | ID | Task | Kind | Status |
|---|----|------|------|--------|
| 1 | H-006 | Attorney + ADR-0008 (blocks public beta) | Hard · legal | 🔲 |
| 2 | H-022 | License ADR attorney review | Hard · legal | 🔲 |
| 3 | H-023 / R-Audit-8.9 | TERMS + legal packet sign-off (F-010) | Hard · legal | 🔲 |
| 4 | H-007 | Approve ADR-0001 / S1 (after `validate-bootstrap --quick`) | Soft · bootstrap | 🔲 |
| 5 | H-003 | Branch protection (`setup-github-repo.sh`) | Soft · GitHub | 🔲 |
| 6 | H-004 | Provision VPS (Oracle / Hetzner) | Soft · ops | 🔲 |
| 7 | H-008 | Telegram token in VPS `.env` | Hard · secrets | 🔲 |
| 8 | H-011 | Kraken read-only keys in VPS `.env` | Hard · secrets | 🔲 |
| 9 | PF-H1 | Optional: CoinMarketCal / Coindar API keys (calendar wizard; CI ok without) | Soft · optional | 🔲 |
| 10 | CEX-P3c | Optional: pay for per-venue historical packs | Soft · cost | 🔲 |
| 11 | H-010 | Explicit live-trading approval (mode=live) | Hard · go-live | 🔲 |
| 12 | H-028 | Per-exchange `go-live-gate.sh --approve` (every venue) | Hard · go-live | 🔲 |
| 13 | H-032 / CEX-P4b | Worldwide trading ack + CEXes beyond nine (P1-first) | Hard · expand CEX | 🔲 |
| 14 | H-035 / H-036 | DEX live program + live swap approve | Hard · expand DEX | 🔲 |
| 15 | DEX-P4a | Enable `trading_enabled` Arbitrum / Ethereum after Base proven | Hard · expand DEX | 🔲 |
| 16 | H-017 | CoinStats parity compare + cancel sub (**deferred**) | Soft · deferred | 🔲 |
| 17 | H-026 | Monthly: portfolio integrity report | Recurring | 🔲 |
| 18 | H-027 | Monthly: VPS cost ≤ $10 | Recurring | 🔲 |
Founder preflights S0–S12: fold into #4–#8 as you run `python scripts/founder_gate.py status`. Local preview: [`docs/LOCAL_DEV.md`](docs/LOCAL_DEV.md) · Post-delivery: [`docs/POST_DELIVERY_PLAN.md`](docs/POST_DELIVERY_PLAN.md).

---

## Open work

### Multi-venue parity (AGENT / Cloud — after Human #13–#15 where gated)

- 🔲 [AGENT][CLOUD] DEX-P4b New swap plugins after P1–P2 — scope: `src/trendalgo/venues/`

### Maintenance cadence

| Cadence | Owner | Item |
|---------|-------|------|
| Weekly | AUTO | `check_risk_mitigations.py` · CI/CodeQL on `main` · Dependabot triage |
| Monthly | AUTO / Human #17–#18 | portfolio integrity · production cost · backup dry-run (R-020) |
| Pre-live | AUTO + Human #11–#12 | `go-live-gate.sh --check-only` → `--approve` |
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
| UX-006 | Scanner chrome: action buttons; board filters + 2-col Settings; Status dialog | done |
| UX-007 | Backtest chrome: same strip pattern; Color ranks/Perfect in Settings Results view | done |
<!-- /ux-inventory -->

## News inbox (synced)

P1/P2 tasks auto-synced by News Bot from [`docs/NEWS_INBOX.md`](docs/NEWS_INBOX.md).

> Security onboarding API-key hygiene (news P2) archived in COMPLETED_TASKS.md (2026-11-15).
