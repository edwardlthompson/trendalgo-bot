# TrendAlgo Bot — BUILD_PLAN

<!-- remaining-tally -->
**Remaining:** AGENT 1 · LOCAL 0 · CLOUD 1 · AUTO 0 · HUMAN 0 · ADB 0 · **1 open**
<!-- /remaining-tally -->
<!-- tally note: DEX-P4b CLOUD; Sprint Audit-2026-11 + Sprint Avalonia-gaps + Sprint Polish-2026-11 + Sprint Polish2-2026-11 + Sprint Polish3-2026-11 + Sprint Polish4-2026-11 + Sprint Polish5-2026-11 archived -->
> **Detail:** [`docs/specs/audit-remediation.md`](docs/specs/audit-remediation.md) · [`docs/CANONICAL_PLAN.md`](docs/CANONICAL_PLAN.md) · **Human gates:** [`docs/HUMAN_BACKLOG.md`](docs/HUMAN_BACKLOG.md) · **Risks:** [`docs/RISK_REGISTER.md`](docs/RISK_REGISTER.md)
> **Completed work:** [`COMPLETED_TASKS.md`](COMPLETED_TASKS.md) · **Post-delivery:** [`docs/POST_DELIVERY_PLAN.md`](docs/POST_DELIVERY_PLAN.md) · **Exchange:** [`docs/EXCHANGE_ROADMAP.md`](docs/EXCHANGE_ROADMAP.md) · **DEX:** [`docs/DEX_ROADMAP.md`](docs/DEX_ROADMAP.md) · **Support:** [`docs/SUPPORT_MATRIX.md`](docs/SUPPORT_MATRIX.md)
> **Sprint Polish7-2026-11** archived in COMPLETED_TASKS.md (POL7-01, 2026-11-26).
> **Sprint Polish6-2026-11** archived in COMPLETED_TASKS.md (POL6-01…03, 2026-11-24).
> **Sprint Portfolio-2026-11** archived in COMPLETED_TASKS.md (PF6-01…04, 2026-11-24).
> **Sprint Polish5-2026-11** archived in COMPLETED_TASKS.md (POL5-01…05, 2026-11-24).
> **Sprint Polish4-2026-11** archived in COMPLETED_TASKS.md (POL4-01…06, 2026-11-24).
> **Sprint Polish3-2026-11** archived in COMPLETED_TASKS.md (POL3-01…04, 2026-11-24).
> **Sprint Polish2-2026-11** archived in COMPLETED_TASKS.md (POL2-01…04, 2026-11-24).
> **Sprint Polish-2026-11** archived in COMPLETED_TASKS.md (POL-01…05, 2026-11-24).
> **Sprint Audit-2026-11** archived in COMPLETED_TASKS.md (AUD-01…17, 2026-11-23).
> **Sprint Avalonia-gaps** archived in COMPLETED_TASKS.md @ `fc9b718` (AV-G-TF1…OTH5, 2026-11-19). Gap file: [`docs/AVALONIA_PARITY_GAPS.md`](docs/AVALONIA_PARITY_GAPS.md).
> **Sauce / Market Context / logos** archived in COMPLETED_TASKS.md @ `665d6f5` · v1.15.2.
> **Multi-venue Sequential (CEX/DEX/TF)** archived in COMPLETED_TASKS.md (2026-11-15).
> **TradFi top-500 + Forex research (TF-P5…P11 + FX-P1…P4)** archived in COMPLETED_TASKS.md @ `54b409c` (2026-11-15).
> **Scan UX desk + AlgoSpecial Forex H1 (UX-S1…S7 + FX-AS1…AS5)** archived in COMPLETED_TASKS.md @ `54b409c` (2026-11-15).
> **Honesty DoD (every multi-venue AGENT row):** bump [`support_matrix.json`](src/trendalgo/device/data/support_matrix.json) + [`docs/SUPPORT_MATRIX.md`](docs/SUPPORT_MATRIX.md) + README Exchange / today / coming-soon + `about_line` when capability changes; scoped `test_support_matrix.py` green.

### Product (do not drift)

<!-- product-brief-sync:begin -->
> Read `AGENT.md` before any sprint row.

**One-liner:** Self-hosted crypto trading platform: native CCXT engine, LTS opportunity scanner, Secret Sauce Lab, and desktop shell.
**Do not drift:** crypto, trading, scanner, portfolio

**Rules:**
- Dry-run is the default; live orders require `TRENDALGO_MODE=live` and per-exchange `go-live-gate.sh --approve`.
- Secret Sauce must beat fees and Buy & Hold under an honest Oracle ceiling (never force-sorted).
- Dual-runtime desktop architecture (ADR-0021): C# Avalonia shell + permanent Python Research Engine sharing `results.db`.
- Do not overwrite live `branding/assets/*.svg` (Sacred vector SoT).

**First milestone:** Kraken public research desk + 9-CEX read-only portfolio + Secret Sauce Lab + Avalonia/PySide6 desktop parity.
<!-- product-brief-sync:end -->

## Now

> Day-to-day device: `.\scripts\packaging\relaunch-device.ps1` (source-first; no PyInstaller) · Avalonia: `dotnet build shell/TrendAlgo.Shell` then relaunch.
> Avalonia-gaps LOCAL complete. Follow-ups: LIVE/NOTIF polish; H-006b; CLOUD DEX-P4b.

| Marker | State |
|--------|-------|
| 🔲 | Open |
| ✅ | Done |
| ❌ | Blocked |

### Sequential (agent)

> **Sprint Polish7-2026-11** archived in COMPLETED_TASKS.md — no open LOCAL POL7-* rows. Index was POL7-01.
> **Sprint Polish6-2026-11** archived in COMPLETED_TASKS.md — no open LOCAL POL6-* rows. Index was POL6-01…03.
> **Sprint Portfolio-2026-11** archived in COMPLETED_TASKS.md — no open LOCAL PF6-* rows. Index was PF6-01…04.
> **Sprint Polish5-2026-11** archived in COMPLETED_TASKS.md — no open LOCAL POL5-* rows. Index was POL5-01…05.
> **Sprint Polish4-2026-11** archived in COMPLETED_TASKS.md — no open LOCAL POL4-* rows. Index was POL4-01…06.
> **Sprint Polish3-2026-11** archived in COMPLETED_TASKS.md — no open LOCAL POL3-* rows. Index was POL3-01…04.
> **Sprint Polish2-2026-11** archived — no open LOCAL POL2-* rows. Index was POL2-01…04.
> **Sprint Polish-2026-11** archived — no open LOCAL POL-* rows. Index was POL-01…05.
> **Sprint Audit-2026-11** archived — no open LOCAL AUD-* rows. Index was AUD-01…17.
> **Sprint Avalonia-gaps** archived — no open LOCAL AV-G-* rows. Index was AV-G-TF1…OTH5.

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
### Local agent (This Computer)

Standing queue for This Computer. Rows: `🔲 [AGENT][LOCAL] … — scope: path`.

<!-- local-agent-lane:begin -->
_No local agent items._
<!-- local-agent-lane:end -->

### Cloud agent (Cursor Cloud)

Standing queue for Cursor Cloud. Rows: `🔲 [AGENT][CLOUD] … — scope: path`.

<!-- cloud-agent-lane:begin -->
_No cloud agent items._
<!-- cloud-agent-lane:end -->

### Open PRs (synced)

> Auto-managed. Do not hand-edit inside the markers.

<!-- open-prs-sync:begin -->
_No open Dependabot or Release Please PRs._
<!-- open-prs-sync:end -->

### Template gaps (synced)

> Auto-managed. Do not hand-edit inside the markers.

<!-- template-gaps-sync:begin -->
_No template gaps._
<!-- template-gaps-sync:end -->
