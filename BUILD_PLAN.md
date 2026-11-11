# TrendAlgo Bot — BUILD_PLAN

<!-- remaining-tally -->
**Remaining:** AGENT 55 · LOCAL 55 · CLOUD 0 · AUTO 0 · HUMAN 2 · ADB 0 · **57 open**
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
> **Active:** Audit remediation Phases 1–9 — [`docs/specs/audit-remediation.md`](docs/specs/audit-remediation.md).
> Sequencing: P1→P5 sequential; P6–P9 after P5. AUTH-01 before BILL-04; SIM-01/02 before BILL-01; SIM-05/06 before LIVE-01.
> Sauce Phase 2–4 backlog: [`docs/specs/secret-sauce-oracle-gap.md`](docs/specs/secret-sauce-oracle-gap.md) — not scheduled.

| Marker | State |
|--------|-------|
| 🔲 | Open |
| ✅ | Done |
| ❌ | Blocked |

### Sprint Audit-P1 — Security surface (Sequential)

1. ✅ [AGENT][LOCAL] AUTH-01 Authenticate mutating endpoints via `require_owner` at router include — scope: `src/trendalgo/api/deps.py`, `api/app.py`, `tests/test_api/`
2. ✅ [AGENT][LOCAL] AUTH-02 Bind prod API to loopback; document SSH/Tailscale — scope: `docker/docker-compose.prod.yml`, `README.md`
3. ✅ [AGENT][LOCAL] AUTH-03 Kill CORS wildcard default — scope: `src/trendalgo/api/app.py`, tests
4. ✅ [AGENT][LOCAL] AUTH-04 Harden TradingView webhook (body-once, HMAC, rate limit tests) — scope: `api/routes/webhooks.py`, `signals/tradingview.py`
5. ✅ [AGENT][LOCAL] AUTH-05 Owner session bearer tokens (keyring, rotate, revoke) — scope: `botd/pairing.py`, device session/keyring

### Sprint Audit-P2 — Remove PWA scaffolding

1. ✅ [AGENT][LOCAL] PWA-01 Delete dead web surface (modules/web, web check scripts/libs) — scope: `modules/web/`, `scripts/check-*web*`, `scripts/lib/*web*`
2. ✅ [AGENT][LOCAL] PWA-02 Delete web-only golden-path schemas after grep clear — scope: `schemas/golden-path/`
3. ✅ [AGENT][LOCAL] PWA-03 Sweep refs; delete `api/routes/ws.py`; preserve Argus README/TEMPLATE — scope: workflows, README, `TEMPLATE_INDEX.json`, `AGENTS.md`
4. ✅ [AGENT][LOCAL] PWA-04 Amend ADR-0016: desktop stays for Study UI — scope: `docs/adr/0016-headless-bot-local-device.md`

### Sprint Audit-P3 — License (ELv2 approved 2026-11-11)

1. ✅ [AGENT][LOCAL] LIC-01 Swap to Elastic License 2.0 — scope: `LICENSE`, `pyproject.toml`, REUSE, CITATION license fields, README badge, `docs/LICENSE_MODEL.md`
2. ✅ [AGENT][LOCAL] LIC-02 Supersede ADR-0005 license clause; single license answer — scope: `docs/adr/`, `CONTRIBUTING.md`

### Sprint Audit-P4 — Risk engine (test-first)

1. 🔲 [AGENT][LOCAL] RISK-01 Slippage on notional — scope: `backtest/slippage.py`
2. 🔲 [AGENT][LOCAL] RISK-02 Stop double-counting equity — scope: `risk/manager.py`
3. 🔲 [AGENT][LOCAL] RISK-03 Daily loss cap inline rollover — scope: `risk/manager.py`
4. 🔲 [AGENT][LOCAL] RISK-04 Circuit breaker re-arm; peak persists — scope: `risk/manager.py`
5. 🔲 [AGENT][LOCAL] RISK-05 `compute_stake` never returns 0.0 — scope: `risk/manager.py`, `trading/sizing.py`
6. 🔲 [AGENT][LOCAL] RISK-06 Windowed failure rate trips — scope: `trading/order_guard.py`
7. 🔲 [AGENT][LOCAL] RISK-07 Directional ticker freshness — scope: `trading/sizing.py`
8. 🔲 [AGENT][LOCAL] RISK-08 Force-trade via `compute_stake` — scope: `api/routes/bots.py`
9. 🔲 [AGENT][LOCAL] RISK-09 Exchange-side reduce-only stops + adopt on restart — scope: trading/risk + ADR-0016 amend
10. 🔲 [AGENT][LOCAL] RISK-10 Panic verify cancel then flatten — scope: `trading/panic.py`

### Sprint Audit-P5 — Simulator + Secret Sauce honesty

1. 🔲 [AGENT][LOCAL] SIM-01 Next-bar-open fills — scope: `backtest/ta_simulator.py`, `sim_accel.py`
2. 🔲 [AGENT][LOCAL] SIM-02 Slippage bps + intrabar stops/gaps — scope: `backtest/ta_simulator.py`
3. 🔲 [AGENT][LOCAL] SIM-03 Validate with `eval_params()` — scope: `backtest/secret_sauce_validate.py`
4. 🔲 [AGENT][LOCAL] SIM-04 Relax spectrum gate; honest oracle losers — scope: `secret_sauce_validate.py`
5. 🔲 [AGENT][LOCAL] SIM-05 Holdout as selection constraint — scope: `secret_sauce_lab/search.py`, `run.py`
6. 🔲 [AGENT][LOCAL] SIM-06 Per-bar causal regime — scope: `secret_sauce_lab/regime_snapshot.py`, `run.py`
7. 🔲 [AGENT][LOCAL] SIM-07 Fee drag, exposure, excess vs hold — scope: `search.py`, result rows
8. 🔲 [AGENT][LOCAL] SIM-08 Permutation null + stability — scope: `search.py`
9. 🔲 [AGENT][LOCAL] SIM-09 Exact coverage metric — scope: `secret_sauce_lab/label_rules.py`
10. 🔲 [AGENT][LOCAL] SIM-10 Dry-run parity with paper fills — scope: `trading/runner/dry_run.py`
11. 🔲 [AGENT][LOCAL] SIM-11 Decay monitor — scope: bot health / may share FEAT-06

### Sprint Audit-P6 — Billing (after AUTH-01 + SIM-01/02)

1. 🔲 [AGENT][LOCAL] BILL-01 Alpha Share excess default — scope: `billing/rules.py`, profit/statements/scheduler/store/schema
2. 🔲 [AGENT][LOCAL] BILL-02 Persist benchmark refs — scope: statements + `venue_attribution.py`
3. 🔲 [AGENT][LOCAL] BILL-03 Caps and floors — scope: `billing/rules.py`
4. 🔲 [AGENT][LOCAL] BILL-04 Statement integrity (hash-chain, recompute, sign) — scope: billing + API (needs AUTH-01)
5. 🔲 [AGENT][LOCAL] BILL-05 Monotonic day counter — scope: `billing/license_gate.py`
6. 🔲 [AGENT][LOCAL] BILL-06 Identity binding + seats — scope: billing enrollment
7. 🔲 [AGENT][LOCAL] BILL-07 Two-class pricing page — scope: device/docs monetization UI
8. 🔲 [AGENT][LOCAL] BILL-08 Evasion coverage table — scope: `docs/MONETIZATION.md`

### Sprint Audit-P7 — Living bot + notifications (after SIM-05/06)

1. 🔲 [AGENT][LOCAL] LIVE-01 Retune scheduler — scope: `botd/` retune
2. 🔲 [AGENT][LOCAL] LIVE-02 Promotion gate — scope: `botd/shadow_gate.py`, `shadow_divergence.py`
3. 🔲 [AGENT][LOCAL] LIVE-03 Anti-thrash — scope: retune dwell/hysteresis
4. 🔲 [AGENT][LOCAL] LIVE-04 Regime flips before retunes — scope: regime actions
5. 🔲 [AGENT][LOCAL] LIVE-05 Honesty in Study UI — scope: device Study
6. 🔲 [AGENT][LOCAL] NOTIF-01 Re-fit notification pipeline — scope: notifications sinks
7. 🔲 [AGENT][LOCAL] NOTIF-02 Event taxonomy + severity — scope: notifications
8. 🔲 [AGENT][LOCAL] NOTIF-03 Re-fit events are billing journal events — scope: billing journal

### Sprint Audit-P8 — Features

1. 🔲 [AGENT][LOCAL] FEAT-01 Deterministic journal replay — scope: journal/store
2. 🔲 [AGENT][LOCAL] FEAT-02 Shadow-to-live promotion gate (generic) — scope: `botd/shadow_gate.py`
3. 🔲 [AGENT][LOCAL] FEAT-03 Fee-aware routing — scope: routing/fees
4. 🔲 [AGENT][LOCAL] FEAT-04 Beta-weighted exposure cap — scope: risk
5. 🔲 [AGENT][LOCAL] FEAT-05 Adaptive bot budgeting — scope: bots scheduler
6. 🔲 [AGENT][LOCAL] FEAT-06 Strategy decay monitor — scope: bot health (w/ SIM-11)

### Sprint Audit-P9 — Housekeeping

1. 🔲 [AGENT][LOCAL] HOUSE-01 SQLite migrations via user_version — scope: PortfolioStore
2. 🔲 [AGENT][LOCAL] HOUSE-02 WAL + busy_timeout — scope: PortfolioStore connect
3. 🔲 [AGENT][LOCAL] HOUSE-03 Risk-core coverage gates — scope: pytest cov config
4. 🔲 [AGENT][LOCAL] HOUSE-04 Fix `httpx2` typo — scope: dependency manifest
5. 🔲 [AGENT][LOCAL] HOUSE-05 Align Python version truth — scope: pyproject + README
6. 🔲 [AGENT][LOCAL] HOUSE-06 Wire or delete `balance_check.py` — scope: pre-trade
7. 🔲 [AGENT][LOCAL] HOUSE-07 Re-enable gates on vendored runner (per-file ignores) — scope: lts_vendor
8. 🔲 [AGENT][LOCAL] HOUSE-08 Kill dead Postgres dual-write — scope: store dual-write
9. 🔲 [AGENT][LOCAL] HOUSE-09 Doc sprawl Argus-safe (archive specs; keep `.agent/`/argus) — scope: `docs/archive/`

### Sprint Market-Context (done)

1. ✅ [AGENT][LOCAL] Analytics core: classic pivots, consensus, regime labels, R:R, VWAP/VP/extension/corr/spread + `MarketContext` — scope: `src/trendalgo/analytics/`, `tests/test_analytics/`
2. ✅ [AGENT][LOCAL] MarketContextPane (4 zones + collapse prefs) — scope: `src/trendalgo/device/views/market_context_pane.py`, `results_view_prefs.py`, `strings.py`
3. ✅ [AGENT][LOCAL] Wire Backtest tab + persist context — scope: `pair_strategy_scan.py`, `pair_strategy_scan_job.py`, `backtest_page.py`, `last_pair_backtest.py`
4. ✅ [AGENT][LOCAL] Wire Scanner Results + stamp `coin["market_context"]` — scope: `scanner_all_ta_coin.py`, `scanner_all_ta_bt.py`, `bridge.py`, `scanner_results.py`
5. ✅ [AGENT][LOCAL] Show Chart overlays for pivots/VWAP/VP — scope: `scanner_chart_dialog.py`, `scanner_chart_trades.py`
6. ✅ [AGENT][LOCAL] Secret Sauce Lab causal pivot/VWAP/VP keys (sparse; residual-gated; no consensus dump) — scope: `secret_sauce_pivots.py`, `secret_sauce_features.py`
7. ✅ [AGENT][LOCAL] Gates + smoke-sprint — scope: `watch-agent-gates`, `smoke-sprint --require`
8. ✅ [AGENT][LOCAL] Scanner Qualified Buy picks band (collapsible; Market Context Buy + TA%) — scope: `buy_picks.py`, `buy_picks_pane.py`, `scanner_page.py`

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
