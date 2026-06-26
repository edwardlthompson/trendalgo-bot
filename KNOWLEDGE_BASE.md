# Knowledge Base — TrendAlgo Bot

> Debug playbooks. Append KB-### entries as issues are resolved.

## KB-001 — Windows without WSL/bash

**Symptom:** Gate scripts fail with WSL "no installed distributions".

**Fix:** Use `python3 scripts/founder_gate.py` and `python3 scripts/check_risk_mitigations.py` directly. Script stubs return SCHEDULED (exit 2) when bash unavailable but file exists.

## KB-002 — Dry-run vs live

**Symptom:** Unclear if bot can place real orders.

**Fix:** `TRENDALGO_MODE=dry-run` and Freqtrade `--dry-run` until `go-live-gate.sh --approve` (H-010). See `docs/RUNBOOK.md`.

## KB-003 — Kraken pair naming

**Symptom:** Backtest fails on pair symbol.

**Fix:** Use `BTC/USD` not `BTC/USDT` on Kraken spot. See `docs/FREQTRADE_INTEGRATION.md`.

## KB-004 — Production on PR hardware

**Symptom:** Considering running live bot at home in Puerto Rico.

**Fix:** **Rejected** (ADR-0002). Use Oracle Always Free or Hetzner VPS only.

## KB-005 — License / MSB concerns

**Symptom:** Want auto-deduct fees from exchange.

**Fix:** **Rejected** (ADR-0008, R-006 eliminated). User-initiated settlement only. Run `check-legal-compliance.sh`.

## KB-006 — Community strategy imports

**Symptom:** Request for marketplace uploads.

**Fix:** **Rejected** (ADR-0009). AI-recommended curated strategies only (S11).

## KB-007 — Post-S12 audit (2026-06-25)

**Symptom:** `/audit` on Windows; bash gates fail; BUILD_PLAN shows complete but founder gates backlog.

**Fix:** Use `python scripts/run-trendalgo-tests.py`, `python scripts/check_risk_mitigations.py --strict --all`, and `python scripts/founder_gate.py status`. Clear human gates via [`docs/HUMAN_BACKLOG.md`](docs/HUMAN_BACKLOG.md) before go-live. CORS: set `TRENDALGO_CORS_ORIGINS` in production `.env`.

## KB-008 — Post–exchange-doc audit (2026-06-25)

**Symptom:** README/BUILD_PLAN describe native CCXT pivot but secondary docs still mention Freqtrade.

**Fix:** R-Audit-2 synced START_HERE, ARCHITECTURE, GITHUB_ABOUT, FEATURE_ROADMAP, pyproject. S13–S18 completed registry + native runner work.

## KB-009 — Post–S18 audit (2026-06-25)

**Symptom:** `/audit` (R-Audit-3) on Windows; README roadmap still "Kraken today"; POST_DELIVERY snapshot stale; THREAT_MODEL/LOCAL_DEV Freqtrade refs; bash gates need WSL.

**Fix:** R-Audit-3 synced README, POST_DELIVERY_PLAN, EXCHANGE_ROADMAP success criteria, THREAT_MODEL, LOCAL_DEV, ROADMAP_PUBLIC. Use `python scripts/run-trendalgo-tests.py`, `python scripts/founder_gate.py status`. Clear **H-030–H-034** via [`docs/HUMAN_BACKLOG.md`](docs/HUMAN_BACKLOG.md) before live worldwide trading. Enable Dependabot in GitHub settings.

## KB-010 — v0.1.0 ship (2026-06-25)

**Symptom:** `/ship` on Windows; pre-release gate needs bash + optional npm; CI must pass post-push.

**Fix:** Pushed `chore(release): prepare v0.1.0` to `main`. Follow-up CI commits fix ruff + workflow (web/python only). Re-run `bash scripts/check-github-ci.sh --wait 600` after CI green. Enable Dependabot alerts; merge Release Please PR for tag.

## KB-011 — Post–DEX program audit (2026-06-26)

**Symptom:** `/audit` (R-Audit-4) on Windows; README/POST_DELIVERY/ROADMAP_PUBLIC stale after S21–S24; bash gates need WSL.

**Fix:** R-Audit-4 synced README (DEX capabilities + roadmap), POST_DELIVERY snapshot (170 tests, DEX row), ROADMAP_PUBLIC Phase 8, HUMAN_BACKLOG H-035/H-036. Use `python scripts/run-trendalgo-tests.py`, `python scripts/founder_gate.py preflight H-035|H-036`. Clear **H-032, H-035, H-036** via [`docs/HUMAN_BACKLOG.md`](docs/HUMAN_BACKLOG.md) before live trading.

## Template KB entries

Legacy template entries (KB-007+) remain in git history; TrendAlgo-specific entries start at KB-001 above.
