# TrendAlgo Bot — BUILD_PLAN

<!-- remaining-tally -->
**Remaining:** AGENT 0 · LOCAL 0 · CLOUD 0 · AUTO 0 · HUMAN 0 · ADB 0 · **0 open**
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

> **Sprint Sauce-Oracle-Gap** — close Oracle gap (phased). Spec: [`docs/specs/secret-sauce-oracle-gap.md`](docs/specs/secret-sauce-oracle-gap.md).
> Prior **Sprint Oracle-SS** archived in COMPLETED_TASKS.md @ `8ba0e76`.
> Open HUMAN: PF-H1 (optional calendar keys) + carry-forward / R-Audit-8.9.

| Marker | State |
|--------|-------|
| 🔲 | Open |
| ✅ | Done |
| ❌ | Blocked |
### Sequential — Sauce Oracle gap

✅ [AGENT][LOCAL] Phase 0 residual instrumentation — dossier residual indexes + feature hits + Study surface — scope: `src/trendalgo/backtest/secret_sauce_dossier.py`, `src/trendalgo/backtest/secret_sauce_lab/residual_instrument.py`, `src/trendalgo/backtest/secret_sauce_lab/run.py`, `src/trendalgo/backtest/secret_sauce_lab/refine_pack.py`, `src/trendalgo/device/views/secret_sauce_study.py`, `tests/test_backtest/test_residual_instrument.py`

✅ [AGENT][LOCAL] Phase 1 residual miner + adaptive exits — AND residual conjunct + `adaptive_exit` family + exit-preferential search — scope: `src/trendalgo/backtest/secret_sauce_lab/residual_mine.py`, `src/trendalgo/backtest/secret_sauce_lab/families.py`, `src/trendalgo/backtest/secret_sauce_lab/search.py`, `src/trendalgo/backtest/secret_sauce_lab/regime_snapshot.py`, `tests/test_backtest/test_residual_mine.py`, `tests/test_backtest/test_adaptive_exit_family.py`

> Phase 2–4 backlog (holdout-aware search, multi-TF arming, CCI/WILLR/MFI, ensemble) documented in [`docs/specs/secret-sauce-oracle-gap.md`](docs/specs/secret-sauce-oracle-gap.md) — not scheduled.

🔲 [HUMAN] PF-H1 Optional: mint CoinMarketCal and/or Coindar API keys for live calendar (wizard walks signup; not required for empty-state CI) — see [`docs/HUMAN_BACKLOG.md`](docs/HUMAN_BACKLOG.md)

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
