# TrendAlgo Bot — BUILD_PLAN

<!-- remaining-tally -->
**Remaining:** AGENT 1 · LOCAL 0 · CLOUD 1 · AUTO 0 · HUMAN 0 · ADB 0 · **1 open**
<!-- /remaining-tally -->
<!-- tally note: DEX-P4b CLOUD after Scan UX + AlgoSpecial FX ✅ -->
> **Detail:** [`docs/specs/audit-remediation.md`](docs/specs/audit-remediation.md) · [`docs/CANONICAL_PLAN.md`](docs/CANONICAL_PLAN.md) · **Human gates:** [`docs/HUMAN_BACKLOG.md`](docs/HUMAN_BACKLOG.md) · **Risks:** [`docs/RISK_REGISTER.md`](docs/RISK_REGISTER.md)
> **Completed work:** [`COMPLETED_TASKS.md`](COMPLETED_TASKS.md) · **Post-delivery:** [`docs/POST_DELIVERY_PLAN.md`](docs/POST_DELIVERY_PLAN.md) · **Exchange:** [`docs/EXCHANGE_ROADMAP.md`](docs/EXCHANGE_ROADMAP.md) · **DEX:** [`docs/DEX_ROADMAP.md`](docs/DEX_ROADMAP.md) · **Support:** [`docs/SUPPORT_MATRIX.md`](docs/SUPPORT_MATRIX.md)
> **Sauce / Market Context / logos** archived in COMPLETED_TASKS.md @ `665d6f5` · v1.15.2.
> **Multi-venue Sequential (CEX/DEX/TF)** archived in COMPLETED_TASKS.md (2026-11-15).
> **TradFi top-500 + Forex research (TF-P5…P11 + FX-P1…P4)** archived in COMPLETED_TASKS.md @ `54b409c` (2026-11-15).
> **Scan UX desk + AlgoSpecial Forex H1 (UX-S1…S7 + FX-AS1…AS5)** archived in COMPLETED_TASKS.md @ `54b409c` (2026-11-15).
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
> Follow-ups: LIVE/NOTIF botd cron wiring; SIM snapshot regen; H-006b before non-owner billing (ADR-0020 Tier B).

| Marker | State |
|--------|-------|
| 🔲 | Open |
| ✅ | Done |
| ❌ | Blocked |
### Sequential (agent)

> Local Sequential clear. Next AGENT work is `[CLOUD]` DEX-P4b under Open work (skipped on This Computer `/build`).

### Human work (complete in this order)

> Single pack for all founder actions. Soft/optional first only when it unblocks nothing critical — **legal → ops → secrets → live → expand**. Detail + approve CLI: [`docs/HUMAN_BACKLOG.md`](docs/HUMAN_BACKLOG.md) · [`docs/FOUNDER_GATES.md`](docs/FOUNDER_GATES.md). Hard gates never AUTO.

| # | ID | Task | Kind | Status |
|---|----|------|------|--------|
| 1 | H-006b | Tier B: counsel/clinic before non-owner billing | Hard · legal Tier B | 🔲 |
| 2 | H-004 | Provision VPS (Oracle / Hetzner) | Soft · ops | 🔲 |
| 3 | H-011 | Kraken read-only keys in VPS `.env` | Hard · secrets | 🔲 |
| 4 | CEX-P3c | Optional: pay for per-venue historical packs | Soft · cost | 🔲 |
| 5 | H-010 | Explicit live-trading approval (mode=live) | Hard · go-live | 🔲 |
| 6 | H-028 | Per-exchange `go-live-gate.sh --approve` (every venue) | Hard · go-live | 🔲 |
| 7 | H-032 / CEX-P4b | Worldwide trading ack + CEXes beyond nine (P1-first) | Hard · expand CEX | 🔲 |
| 8 | H-035 / H-036 | DEX live program + live swap approve | Hard · expand DEX | 🔲 |
| 9 | DEX-P4a | Enable `trading_enabled` Arbitrum / Ethereum after Base proven | Hard · expand DEX | 🔲 |
| 10 | H-017 | CoinStats parity compare + cancel sub (**deferred**) | Soft · deferred | 🔲 |
| 11 | H-026 | Monthly: portfolio integrity report | Recurring | 🔲 |
| 12 | H-027 | Monthly: VPS cost ≤ $10 | Recurring | 🔲 |
PF-H1 + H-008 + H-003 + Tier A + H-007 archived ✅. Skipped for now (still open): H-006b, H-004, H-011, CEX-P3c.

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
**Hard gates (never AUTO):** H-006, H-006b, H-008, H-010, H-011, H-023, H-028, H-031, H-032, H-036 · Tier A legal closes with `residual-risk owner-only+foss` note (ADR-0020); Tier B billing stays deferred

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

- 🔲 [AGENT][LOCAL] Extend SecretRedactor to wallet private keys, seed phrases and vaulted keys at every log level — scope: src/trendalgo/exchanges/secrets.py (news P2, 2026-11-16) https://cryptowatchdesk.com/news/security-alert-proxima-post-mortem-debug-logs-held-private-keys-5324-sol-181-users-firewall-rule-removed
- 🔲 [AGENT][LOCAL] Confirm agent-framework 1.26.1/1.26.2 is not in uv.lock or on the VPS and rotate credentials if it is — scope: pyproject.toml, uv.lock (news P2, 2026-11-18) https://www.wiz.io/blog/malicious-version-of-microsofts-agent-framework-published-to-pypi
- 🔲 [AGENT][LOCAL] Bump FastAPI to 0.164.0 and set request body size limits — scope: pyproject.toml, src/trendalgo/ (news P2, 2026-11-18) https://github.com/fastapi/fastapi/releases/tag/0.164.0
