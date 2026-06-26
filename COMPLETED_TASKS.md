# Completed Tasks

> Archive of finished BUILD_PLAN items.











## Sprint R-Audit-4 — post DEX program doc sync (2026-06-26)


- **Exit:** Secondary docs reflect S21–S24 completion; KB-011 for Windows gate fallbacks.


- 1. ✅ [AGENT] README — DEX capabilities + roadmap S21–S24 (F-041, F-044, F-045)
- 2. ✅ [AGENT] POST_DELIVERY + ROADMAP_PUBLIC Phase 8 (F-042, F-043)
- 3. ✅ [AGENT] BUILD_PLAN post-delivery + HUMAN_BACKLOG H-035/H-036 (F-046, F-047)
- 4. ✅ [AGENT] KB-011 audit notes + test count sync (F-048)


## Sprint 24 — Live swaps + ops (2026-06-26)


- **Exit:** Per-venue go-live with hard gate.

- **Blocks:** H-036 (DEX live trading hard gate) · H-010 / H-028 per venue

- 1. ✅ [AGENT] Live swap execution behind per-venue `trading_enabled` in venues registry
- 2. ✅ [AGENT] Signer from **`DEX_SIGNER_KEY`** on VPS only (CM-9)
- 3. ✅ [AGENT] Runbook: RPC failover, nonce management, slippage controls
- 4. ✅ [AGENT] CM-6-style multi-chain sync load test + docs sync + LP L2

## Sprint 23 — Dry-run swaps (2026-06-26)


- **Exit:** Swap simulation only — no mainnet broadcast. Covered by **H-035** program approval.

- 1. ✅ [AGENT] `dex/runner/dry_run.py`
- 2. ✅ [AGENT] Uniswap V3 swap plugin (EVM) + Jupiter quote/dry-run (Solana)
- 3. ✅ [AGENT] `DEX_TRADING_ACK` env gate (mirrors `WORLDWIDE_TRADING_ACK`)
- 4. ✅ [AGENT] API `/platform/dex/preview` + `/platform/dex/dry-run` + tests + LP L2

## Sprint 22 — Portfolio plugins (2026-06-26)


- **Exit:** DEX positions surfaced in portfolio API.

- 1. ✅ [AGENT] Uniswap V3 LP positions (EVM chains)
- 2. ✅ [AGENT] 0x quote preview (read-only)
- 3. ✅ [AGENT] Multi-chain sync orchestration + billing attribution by venue
- 4. ✅ [AGENT] Tests + LP L2

## Sprint 21 — Foundation (EVM + Solana wallet read) (2026-06-26)


- **Exit:** Multi-chain wallet balances via plugin registry; refactor S12 `onchain.py` stub.

- **Blocks:** H-035 (DEX program scope) · H-025 (RPC endpoints)

- 1. ✅ [AGENT] `config/venues.registry.json` + `src/trendalgo/venues/` (base, registry loader, plugin ABC)
- 2. ✅ [AGENT] ADR-0011 + refactor `portfolio/onchain.py` → EVM plugins (**ethereum, base, arbitrum**) + **Solana** wallet read
- 3. ✅ [AGENT] RPC config via env (`ETH_RPC_URL`, `BASE_RPC_URL`, `ARB_RPC_URL`, `SOLANA_RPC_URL`)
- 4. ✅ [AGENT] Tests + LP L1

## Sprint 20 — N-Exchange Ops Hardening (2026-06-26)

- ✅ RUNBOOK § Multi-venue trading ops (Phase 2, 9 venues, worldwide ack workflow)
- ✅ CM-6: `run_n_exchange_ops_validation()` — 9+ portfolio sync + trading status gate
- ✅ `scripts/load-test-portfolio-sync.sh` runs combined N-exchange ops check
- ✅ EXCHANGE_ROADMAP Tier D closed; exchange program docs synced
- ✅ 141 tests pass; L2 sign-off (tests + encoding + load script)
- 🔲 Human: H-032 worldwide phase approval for live trading; L2 web preview on founder machine

## Sprint 19 — Phase 2 + Multi-Venue Arbitrage (2026-06-26)

- ✅ Registry v6 — `worldwide_trading_phase: 2`; `trading_enabled` for Bitstamp + Crypto.com
- ✅ Multi-venue arbitrage detector (registry-driven, informational only)
- ✅ `GET /api/v1/trading/arbitrage/signals` trading-lane API
- ✅ 136 tests pass; L2 sign-off (tests + encoding)
- 🔲 Human: H-032 worldwide phase plan approval; L2 web build (`preview-local.ps1`) on founder machine

## Review R-Audit-3 — Post–S18 doc sync (2026-06-25)

- ✅ `CODE_REVIEW.md` written (local, gitignored) — F-021–F-032
- ✅ README portfolio venues + roadmap table (S13–S18 complete, S19–S20 active) — F-021
- ✅ `docs/POST_DELIVERY_PLAN.md` snapshot (130 tests, exchange program) — F-022
- ✅ `docs/EXCHANGE_ROADMAP.md` success criteria + recommendation — F-023
- ✅ `docs/THREAT_MODEL.md`, `docs/LOCAL_DEV.md`, `docs/ROADMAP_PUBLIC.md` — F-024, F-025, F-028
- ✅ `src/trendalgo/__init__.py` docstring; R-039 label in RISK_REGISTER + risk-catalog — F-026, F-029
- ✅ `KNOWLEDGE_BASE.md` KB-009 — F-027, F-030
- 🔲 Human: Dependabot alerts (F-031); founder gates H-030–H-034 (F-032)

## Sprint 18 — Worldwide Phase 1 Trading (2026-06-25)

- ✅ Registry v5 — `trading_enabled` for Binance, Bybit, OKX; `worldwide_trading_phase: 1`
- ✅ `list_worldwide_trading_exchanges()` + dynamic `list_supported_exchanges()`
- ✅ Pair normalization on route/dry-run (`BTC/USD` → `BTC/USDT`)
- ✅ `WORLDWIDE_TRADING_ACK` guard for live on `us_restricted` venues
- ✅ Runner status API: `worldwide_trading_phase`, `worldwide_exchanges`
- ✅ 130 tests pass, ~86% coverage; `.env.example` documents `WORLDWIDE_TRADING_ACK`
- 🔲 Human: H-032 worldwide phase plan approval

## Sprint 17 — US Hardening (2026-06-25)

- ✅ Registry v4 — Bitstamp + Crypto.com portfolio (9 venues total)
- ✅ Dry-run fixtures for bitstamp/cryptocom
- ✅ CM-3: `trading/backtest/walk_forward.py` + native `/research/walk-forward`
- ✅ CM-6: `exchanges/load_test.py`, `load-test-portfolio-sync.sh` (9 exchanges &lt; 30s)
- ✅ `compare-portfolio-parity.sh` multi-exchange mode
- ✅ `check-production-cost.sh` runs load test first
- ✅ Production runbook: multi-exchange sync, CM-3/6 ops (`docs/RUNBOOK.md`)

## Sprint 16 — All US CEX Native Trading (2026-06-25)

- ✅ Registry v3 — `trading_enabled` for Coinbase Advanced + Gemini (Tier B US)
- ✅ `trading/runner/adapters/` — generic CCXT trading adapter + registry
- ✅ `trading/control.py` — per-exchange pause + go-live state
- ✅ API: `/trading/exchanges/control`, pause, go-live, per-exchange route
- ✅ Journal + fee ledger tags: `exchange`, `bot_id`; billing attribution by exchange
- ✅ `go-live-gate.sh --exchange` wires audit + control store
- ✅ CM-2 fixture signal tests for grid + smart-dca
- 🔲 Human: H-010/H-028 per exchange for live enable

## Sprint 15 — Native Runner + FT Removal (2026-06-25)

- ✅ Native strategy runtime (`strategies/runtime/`) — MultiTFExample, SmartDCA, GridTrading ported
- ✅ `risk/strategy_mixins.py` — RiskGuard + ScalePosition mixins
- ✅ `trading/runner/dry_run.py` + `trading/backtest/native_adapter.py` (CM-1)
- ✅ `GET /api/v1/trading/runner/status`, `POST /api/v1/trading/dry-run/tick`
- ✅ Bot orchestrator `engine` + `exchange` columns; PWA `native` badge
- ✅ CM-4: deleted `user_data/`, FREQTRADE_INTEGRATION.md, FT docker services, FT pyproject refs
- ✅ `check-legal-compliance.sh` — no freqtrade in src/web; no withdraw in runner
- ✅ `config/bot/*.example.json` replaces user_data configs; backup uses `config/`
- ✅ 106 tests pass, ~85% coverage
- 🔲 Human: H-031 ADR-0010 + FT removal approval; LP L2 sign-off

## Sprint 14 — Worldwide Portfolio (2026-06-25)

- ✅ Registry v2 — 7 portfolio venues (Tier A/B/C): Kraken, Binance.US, Coinbase Advanced, Gemini, Binance, Bybit, OKX
- ✅ `GenericCcxtPortfolioAdapter` — registry-driven CCXT sync for all venues
- ✅ `asset_mapper.py` — ZUSD/XXBT → USD/BTC normalization
- ✅ `pair_normalizer.py` — USD vs USDT quote per exchange
- ✅ `scheduler.py` — staggered sync (CM-6 stub; `TRENDALGO_SYNC_STAGGER_SEC`)
- ✅ Kraken/Binance.US refactored to generic-backed adapters
- ✅ `tests/conftest.py` — zero stagger in tests; 103 tests pass
- 🔲 Human: read-only API keys on venues used; LP L2 sign-off

## Sprint 13 — US Exchange Foundation (2026-06-25)

- ✅ `config/exchanges.registry.json` — Tier A/B catalog (Kraken, Binance.US active)
- ✅ `src/trendalgo/exchanges/` — registry, base protocol, sync orchestration
- ✅ `exchanges/adapters/kraken.py` — refactored from `portfolio/sync.py`
- ✅ `exchanges/adapters/binanceus.py` — replaces global `binance` stub
- ✅ `GET /api/v1/exchanges/registry` + PWA accounts panel with brand names
- ✅ `sync_all_exchanges` registry-driven; trading router `binanceus`
- ✅ Arbitrage detector uses `binanceus` (informational)
- ✅ `tests/test_exchanges/` — 8 new tests; 97 total pass, ~86% coverage
- ✅ `.env.example` + `check-api-key-policy.sh` — BINANCEUS keys
- 🔲 Human: H-030, H-034 before S14 AGENT work

## Review R-Audit-2 — Post–exchange-doc audit (2026-06-25)

- ✅ `CODE_REVIEW.md` written (local, gitignored) — F-011–F-020
- ✅ `docs/START_HERE.md` aligned with native CCXT / README — F-011
- ✅ `docs/ARCHITECTURE.md` updated — native runner, ADR-0010 — F-012
- ✅ `docs/GITHUB_ABOUT.md`, `docs/FEATURE_ROADMAP.md`, `pyproject.toml` description — F-013, F-014, F-016
- ✅ `KNOWLEDGE_BASE.md` KB-008 audit notes — F-017
- ✅ PR template Local Preview checklist — LP protocol item 4
- 🔲 Human: Dependabot alerts (F-018), H-034 L1 preview, H-030 exchange scope (F-020)
- 🔲 Deferred: `binance` → `binanceus` code stub (F-015 → S13); FT removal (F-019 → S15 CM-4)

## Review R-Audit — Full repo audit (2026-06-25)

- ✅ `CODE_REVIEW.md` written (local, gitignored) — F-001–F-010 findings
- ✅ README: root Python test path + `docs/ARCHITECTURE.md` link
- ✅ CORS env gate `TRENDALGO_CORS_ORIGINS` in API + `.env.example`
- ✅ `KNOWLEDGE_BASE.md` KB-007 post-S12 audit notes
- ✅ BUILD_PLAN Archived Sprints table populated (S0–S12 + R-Audit)
- 🔲 Human: founder gates H-001–H-025, Dependabot alerts, H-023/H-025 (see HUMAN_BACKLOG)

## Sprint 12 — Platform Extensions & Risk Register Zero (2026-06-25)

- ✅ On-chain read-only wallet sync (`portfolio/onchain.py`); pair forager prototype (`scanner/forager.py`)
- ✅ Funding rate display + profit hooks; unified multi-exchange trading router (dry-run default)
- ✅ On-chain verifiable fee receipt stubs; on-chain/sentiment data module stub
- ✅ PostgreSQL dual-write adapter, `docker/postgres/schema.sql`, migrate dry-run script
- ✅ `docs/ARCHITECTURE.md` (horizontal scaling); Platform API `/api/v1/platform/*`
- ✅ PWA platform panel (forager, funding, postgres status) on portfolio view
- ✅ Risk Register Zero: `check-risk-mitigations.sh --strict --all` → 0 active risks
- ✅ `tests/test_sprint12/` — 89 tests, ~86% coverage

## Sprint 11 — AI Strategy Curation & Anonymous Growth (2026-06-25)

- ✅ AI recommender, scanner-to-strategy pipeline, curated library, NL draft (rule-based + optional Ollama)
- ✅ Anonymous referral codes + opt-in pseudonymous leaderboard
- ✅ Boost Mode (15% license rate) API
- ✅ Strategies PWA — recommender, curated presets, growth panel
- ✅ `docs/AI_STRATEGIES.md`; `check-legal-compliance.sh` community import scan
- ✅ `tests/test_sprint11/` + API coverage

## Sprint 10 — Performance License & Settlement (2026-06-25)

- ✅ Profit engine, fee ledger, rules (net-loss=$0, carry-forward, drawdown pause)
- ✅ License statements with signed export; enrollment + terms log (install UUID only)
- ✅ Billing API + PWA dashboard, settlement copy/QR, Lightning stub
- ✅ License gate on live trading; grace period + reminders scheduler
- ✅ `TERMS.md` draft; `reconcile-fees.sh`, `check-copy-compliance.sh`
- ✅ `tests/test_billing/` + API coverage

## Sprint 8 — Portfolio Advanced & Multi-Exchange (2026-06-25)

- ✅ Multi-exchange sync (Kraken + Binance sample), spot/futures accounts, aggregated overview
- ✅ Asset tags, manual cost basis, allocation targets, rebalance suggestions (manual apply)
- ✅ YoY/MoM comparisons, performance goals, basket bot weights
- ✅ Cross-exchange arbitrage detector (informational only)
- ✅ Public read-only dashboard tokens; Discord + SMTP test notifiers (env-gated)
- ✅ PWA: accounts, tags filter, goals progress, comparisons, rebalance, arbitrage panels; accent colors
- ✅ `tests/test_sprint8/`, API route coverage

## Sprint 7 — Research, Tax & Export Hub (2026-06-25)

- ✅ Walk-forward, Monte Carlo, portfolio stress MC, hyperopt heatmap grid
- ✅ Correlation matrix + diversification suggestions API + PWA panels
- ✅ Backtest visualizer, research tools panel, backtest share tokens
- ✅ Tax FIFO CSV export, export hub (portfolio, settings, bundle)
- ✅ Exit rules API + config UI; `ScalePositionMixin` for Freqtrade scale-in/out
- ✅ Expanded rule-based AI insights with disclaimer
- ✅ `tests/test_sprint7/`, `tests/test_export/`, API route coverage

## Sprint 6 — Strategy Templates, Multi-Bot & Watchlists (2026-06-25)

- ✅ Template registry + JSON import/export; Smart DCA + Grid Freqtrade strategies
- ✅ Backtest library, slippage/fees, compare, attribution, hyperopt stub
- ✅ Multi-bot orchestrator + dashboard fleet list
- ✅ Custom watchlist alerts, generic signal webhook, market event evaluator
- ✅ Strategies PWA tab — composer, deploy DCA/grid, library clone/compare
- ✅ ATR position sizing module

## Sprint 5 — Portfolio Tracker Core (2026-06-25)

- ✅ Portfolio overview API + default PWA landing (net worth, daily P/L, health score)
- ✅ Holdings, allocation, P/L breakdown, period comparison, equity curve, heatmap, timeline scrubber
- ✅ `portfolio/metrics`, `benchmarks`, `health`, `drawdown`, `snapshots` scheduler + daily Telegram summary
- ✅ Notification inbox, portfolio event alerts, CSV export
- ✅ `scripts/smoke-notifications.sh`, `compare-portfolio-parity.sh`, `check-portfolio-integrity.sh`
- ✅ PWA widget manifest at `examples/web/public/widgets/`

## Sprint 4.5 — Opportunity Scanner (LTS Full Absorption) (2026-06-25)

- ✅ Native LTS port in `src/trendalgo/scanner/` + `vendor_manifest.json` (no submodule)
- ✅ Pipeline, SQLite `scanner.db`, APScheduler, qualified snapshot API (O5)
- ✅ Scanner PWA tab — ranked table, sparklines, settings, watchlist pins
- ✅ BacktestDataLoader, watchlist bridge, OpportunityScannerMixin, alert tiers
- ✅ `strong-uptrend-scanner` template preset; `docs/LTS_ABSORPTION.md`
- ✅ `scripts/lts-parity-check.sh`, `scripts/check_scanner_imports.sh`
- ✅ Scanner unit + API tests

## Sprint 4 — Notifications, Deploy & Portfolio Foundation (2026-06-25)

- ✅ Portfolio SQLite schema + Kraken CCXT sync (dry-run sample + live path)
- ✅ Notification preferences API + PWA push handlers in service worker
- ✅ TradingView webhook (HMAC, rate limit, IP allowlist, audit)
- ✅ AI backtest summary (rule-based + optional Ollama)
- ✅ Backup/restore scripts, health cron, `docker-compose.prod.yml`, systemd unit
- ✅ `scripts/deploy-vps.sh` — external VPS only (ADR-0002)
- ✅ 40+ unit/API tests

## Sprint 3 — Web UI + Unified Bot Dashboard (2026-06-25)

- ✅ FastAPI `/api/v1` — pairs, strategies, backtest, dashboard, risk, debug, WebSocket
- ✅ `src/trendalgo/analytics/metrics.py` — Sharpe, Sortino, Calmar, profit factor, equity curve
- ✅ TrendAlgo PWA — health widget, bot dashboard, backtest charts, risk pause, config form, debug logs
- ✅ Playwright UX smoke (`e2e/dashboard.spec.ts`) + API mocks for CI
- ✅ 30+ Python tests, web vitest + e2e green

## Sprint 2 — Risk, Execution & Paper Trading (2026-06-25)

- ✅ `RiskManager` — stake caps, daily loss, circuit breaker, pause/resume
- ✅ Freqtrade protections + `validate_pre_live` + `RiskGuardMixin` on `MultiTFExample`
- ✅ `TradeJournal` SQLite + fee hook idempotency (R-014 seed)
- ✅ Risk metrics + `get_risk_status` API stub
- ✅ Telegram commands (status/pause/resume; H-008 tokens in human backlog)
- ✅ 22 unit tests, ≥85% coverage on active modules

## Sprint 1 — Core Engine Foundation (2026-06-25)

- ✅ Root `pyproject.toml` + `uv.lock` + CI wired to trendalgo-bot
- ✅ Kraken dry-run config + `MultiTFExample` strategy (5m/1h + LTS mixin)
- ✅ LTS adapter, uniformity, `TrendSpotterMixin`, strategy registry
- ✅ `src/trendalgo/data/download.py`, `schemas/backtest_result.py`
- ✅ 11 unit tests, 93% coverage on active modules
- ✅ `scripts/verify-freqtrade-backtest.sh` (requires separate `freqtrade==2024.12.1` install)

## Sprint 0 — TrendAlgo Initialization (2026-06-25)

- ✅ [AGENT] `init-project.ps1` — TrendAlgo Bot; pruned to python + web stacks
- ✅ [AGENT] Customized README, AGENT_MEMORY, .env.example, KNOWLEDGE_BASE, PROMPT_LIBRARY
- ✅ [AGENT] ADR-0001–0009 in `docs/adr/`; DECISION_LOG entry
- ✅ [AGENT] LEGAL, LEGAL_SAFETY, MONETIZATION, DATA_MINIMIZATION, ROADMAP_PUBLIC, CONTRIBUTING
- ✅ [AGENT] FREQTRADE_INTEGRATION, LTS_INTEGRATION, FEATURE_ROADMAP, PORTFOLIO_TRACKER, LICENSE_MODEL draft
- ✅ [AGENT] Domain scaffold `src/trendalgo/*`, `user_data/`, `docker/` compose templates
- ✅ [AGENT] Feature spec stubs (opportunity-scanner, fee-*, security-onboarding, ai-strategy-recommender, …)
- ✅ [AGENT] THREAT_MODEL, DEPLOYMENT § Oracle, parallel docs
- ✅ [AGENT] Founder gate infra (tasks 20–26, prior session)
- 🔲 [HUMAN] H-004 Oracle provisioning, H-006 attorney, H-001 approve after review
- 🔲 [AUTO] Sprint 0 strict sign-off (task 27) — pending HUMAN gates

## v0.11.0 release (2026-06-18)

- ✅ [HUMAN] Merge Release Please PR #14 — [v0.11.0](https://github.com/edwardlthompson/agent-project-bootstrap/releases/tag/v0.11.0) published
- ✅ [AGENT] Manual version sync on release PR branch (`5fe0fc1`) — Release Please extra-files gap
- ✅ [AUTO] CI + CodeQL + Security Scan green @ 6d4f4ac

## Sprint M29 — Post v0.11.0 release hardening (2026-06-18)

- ✅ [AGENT] Windows-safe `sync-template-version.sh` (quoted heredoc + env var; F-004)
- ✅ [AGENT] Auto-sync version files + SBOM dispatch in `release-please.yml` (F-001/F-002)
- ✅ [AGENT] Rename `health-check.yml` → `weekly-health-check.yml`; add `actions: read` (F-003)
- ✅ [AUTO] SBOM backfill workflow triggered for v0.11.0 (run `27731653800`)

## v0.10.0 release (2026-06-17)

- ✅ [HUMAN] `gh auth refresh -s security_events` (Dependabot API verified)
- ✅ [HUMAN] Merge Release Please PR #13 — [v0.10.0](https://github.com/edwardlthompson/agent-project-bootstrap/releases/tag/v0.10.0) published
- ✅ [AGENT] Sync `.template-version`, `TEMPLATE_INDEX.json`, README badge, `AGENT_MEMORY.md` to 0.10.0 (`36a02e4`)
- ✅ [AGENT] Fix `release.yml` SBOM backfill — checkout `main` when `tag` input set
- ✅ [AGENT] Add `sync-template-version.sh` + `check-template-version-sync.sh` gate
- ✅ [AGENT] `verify-fdroid-metadata.sh` green; no anti-features in template metadata
- ✅ [AUTO] Release workflow SBOM backfill — 7 assets on [v0.10.0](https://github.com/edwardlthompson/agent-project-bootstrap/releases/tag/v0.10.0) (run `27727807142`)
- ✅ [ADB] Device dry-run on CPH2583 (wireless ADB) @ 2026-06-18

## Sprint M28 — Weekly maintain audit (2026-06-18)

- ✅ [AGENT] Index + commit `fdroid-device-dry-run.{sh,ps1}` (CODE_REVIEW F-001/F-002)
- ✅ [AGENT] Fix `UpdateApplierTest` Robolectric FileProvider failure on Windows
- ✅ [AUTO] Security triage + CI green @ f78dd18; 0 Dependabot alerts/PRs
- ✅ [HUMAN] Merge Release Please PR #14 — superseded by v0.11.0 release (2026-06-18)

## BUILD_PLAN cleanup (2026-06-18, M28 complete)

- ✅ [AGENT] Archive M28; extend Archived Sprints row to M19–M28

## Sprint M5 — README Visual Refresh (2026-06-12)

- ✅ [AGENT] Harden `scripts/normalize-markdown-whitespace.py` — table-aware blank-line collapse
- ✅ [AGENT] Add `scripts/check-markdown-tables.sh`; hook into `validate-bootstrap.sh`
- ✅ [AGENT] Redesign README sections — shields.io badges + HTML `<dl>`/tables for What's Included, BUILD_PLAN Labels, Template Update Checker, Supported Stacks
- ✅ [AGENT] Add README badge conventions to `docs/MAINTAINING_THE_TEMPLATE.md`
- ✅ [AGENT] Run verification — encoding, design cohesion, markdown table lint, TEMPLATE_INDEX validation
- ✅ [HUMAN] Visual review on GitHub after push — badges load, links resolve *(closed M14: superseded by maintainer README cycles)*

## Template Maintainer — v0.2.1 Full Bootstrap Hardening (2026-06-13)

- ✅ [AGENT] Normalize `.gitignore` UTF-16 to UTF-8; extend encoding scan and pre-commit hook
- ✅ [AGENT] Sync `PROMPT_LIBRARY.md` entries 4, 6, 8, 9; populate `KNOWLEDGE_BASE.md` (6 entries)
- ✅ [AGENT] Document Lighthouse 3-run median in `modules/web/MODULE.md`
- ✅ [AGENT] SHA-pin `release.yml` actions; add pin policy to `docs/SECURITY_TRIAGE.md`
- ✅ [AGENT] Add `check-workflow-action-ref-format.sh` pre-commit hook
- ✅ [AGENT] Init scripts: `validate-workflow-actions` + `check-github-ci` reminder
- ✅ [AGENT] Devcontainer: encoding check, gh CLI feature, CI gate tip
- ✅ [AGENT] Add `health-check.yml` weekly workflow
- ✅ [AGENT] Bootstrap Gradle wrapper; CI `android-build` assembleDebug job
- ✅ [AGENT] Bump to v0.2.1; sync `TEMPLATE_INDEX.json`, `CHANGELOG.md`, `README.md`
- ✅ [HUMAN] Set GitHub About from `docs/GITHUB_ABOUT.md` (via `gh repo edit`)
- ✅ [HUMAN] Create GitHub Release tag `v0.2.1` (https://github.com/edwardlthompson/agent-project-bootstrap/releases/tag/v0.2.1)
- ✅ [HUMAN] GitHub settings: Dependabot alerts, private vulnerability reporting, branch protection (CI + Security Scan + CodeQL)
- ✅ [HUMAN] Replace `@[PROJECT_OWNER]` in CODEOWNERS with `@edwardlthompson` (template maintainer)

## Template Maintainer — v0.2.0 Backlog Fix (2026-06-12)

- ✅ [AGENT] Normalize UTF-16 files to UTF-8; add `scripts/check-file-encoding.sh` + CI + pre-commit
- ✅ [AGENT] Add `package-lock.json`, `uv.lock`, `.env.example`; expand `validate-bootstrap.sh`
- ✅ [AGENT] Sync `TEMPLATE_INDEX.json` with LICENSE, scripts, workflows, rules
- ✅ [AGENT] Sync README, SECURITY_TRIAGE, RUNBOOK, UPGRADING_FROM_TEMPLATE, PROMPT_LIBRARY, CHANGELOG
- ✅ [AGENT] Harden license-compliance CI; web coverage budget; android ops checklist
- ✅ [AGENT] Harden INITIALIZATION_PROMPT Sections 2/7/8 with Build Verification Gate
- ✅ [AGENT] Update BUILD_PLAN Sprint 0 + Milestone Gates
- ✅ [AGENT] Bump `.template-version` to 0.2.0; finalize CHANGELOG
- ✅ [HUMAN] GitHub settings: Dependabot alerts, private vulnerability reporting, branch protection, About
- ✅ [HUMAN] Replace `@[PROJECT_OWNER]` in CODEOWNERS with `@edwardlthompson`

## Template Maintainer — v0.6.0+ Web Layout & CI Fixes (2026-06-13)

- ✅ [AGENT] Add `docs/WEB_PROJECT_LAYOUT.md` and agent routing for docs/ vs examples/web/
- ✅ [AGENT] Localization scaffold docs (web `locales/` + Android `strings.xml`) separated from styles
- ✅ [AGENT] Android `NetworkStatusMonitor` for online/offline status parity with web
- ✅ [AGENT] Harden `check-design-cohesion` (CSS content guard, main.ts i18n, PS1 parity)
- ✅ [AUTO] CI, Security Scan, CodeQL, and GitHub Pages green on `main` (commit `38ce003`)
- ✅ [HUMAN] Enable GitHub Pages (Actions source) and workflow PR permissions via repo settings

## Sprint M0 — Template Hardening v0.2.2

- ✅ [AGENT] Add `scripts/setup-github-repo.sh` and `scripts/setup-github-repo.ps1` — idempotent Dependabot alerts, private vulnerability reporting, branch protection/rulesets (CI + Security Scan + CodeQL); print UI fallback checklist on API 422
- ✅ [AGENT] Add gitleaks CI job to `.github/workflows/security.yml` (or `ci.yml`) on PR + `main` push
- ✅ [AGENT] Add `check-file-limits` and `validate-bootstrap --quick` to `.pre-commit-config.yaml`
- ✅ [AGENT] Add `scripts/pre-release-gate.sh` and `scripts/pre-release-gate.ps1` — CI poll, Dependabot Critical/High count, template version/tag match, release dry-run reminder
- ✅ [AGENT] Add KNOWLEDGE_BASE KB-007 (npm/pip overrides policy for transitive CVEs); document `@lhci/cli` override in DECISION_LOG
- ✅ [AGENT] Add `npm audit` step to `examples/web` and `uv pip audit` (or equivalent) to weekly `.github/workflows/health-check.yml`
- ✅ [AGENT] Sync `AGENT_MEMORY.md` seed template version with `.template-version`; fix stale `0.1.0` reference
- ✅ [AGENT] Bump `.template-version` to `0.2.2`; update CHANGELOG, TEMPLATE_INDEX, README

## Sprint M1 — Template Hardening v0.3.0

- ✅ [AGENT] Extend `init-project.sh` / `.ps1` with interactive stack picker (web / python / android / multi / none) — prune unused `examples/` and `modules/`, never delete LICENSE/CI/scripts
- ✅ [AGENT] On init: sync `AGENT_MEMORY.md` active modules; emit minimal BUILD_PLAN Parallel section for chosen stack
- ✅ [AGENT] Add `.cursor-session-state.example.json` schema; document restore flow in `docs/FOR_AGENTS.md`
- ✅ [AGENT] Expand `docs/FOR_AGENTS.md` failure playbook (CI poll, GH_TOKEN, Dependabot conflicts, 3-strike escalation, parallel scope collision grep)
- ✅ [AGENT] Add `android-release` CI job — `SOURCE_DATE_EPOCH=1700000000 ./gradlew assembleRelease`, FOSS grep, optional two-run APK hash compare with flake tolerance
- ✅ [AGENT] Enforce `pytest --cov-fail-under=90` in CI for `examples/python`
- ✅ [AGENT] Add Conventional Commits PR title check (`amannn/action-semantic-pull-request`) to `.github/workflows/ci.yml`
- ✅ [AGENT] Draft `docs/adr/0001-core-architecture.md` pattern for child repos (MVVM / Clean / Hexagonal choice template)
- ✅ [AGENT] Bump `.template-version` to `0.3.0`; update CHANGELOG, TEMPLATE_INDEX, README

## Sprint M2 — Template Features v0.4.0

- ✅ [AGENT] Add `modules/node/MODULE.md` and `examples/node/` Golden Path stub (Fastify or Hono, MIT, typed, vitest)
- ✅ [AGENT] Add Node CI job to `.github/workflows/ci.yml` (lint, test, locked install)
- ✅ [AGENT] Add GitHub Pages deploy workflow for `examples/web` demo (FOSS, no tracking)
- ✅ [AGENT] Add Dependabot auto-merge workflow — patch/minor only, requires CI + dependency-review pass, excludes major without `[HUMAN]` label
- ✅ [AGENT] Add changelog automation (`release-please` or `git-cliff`) wired to Conventional Commits
- ✅ [AGENT] Add `scripts/simulate-template-upgrade.sh` — clone, init, cherry-pick per `docs/UPGRADING_FROM_TEMPLATE.md`, assert validate-bootstrap passes
- ✅ [AGENT] Add composite GitHub Action `action.yml` exporting `validate-bootstrap` for downstream repos
- ✅ [AGENT] Bump `.template-version` to `0.4.0`; update CHANGELOG, TEMPLATE_INDEX, README
- ✅ [AUTO] Upgrade simulation test passes in CI (optional scheduled job)
- ✅ [AGENT] GitHub Actions stale bot (`actions/stale`); exempt `template-improvement` (`.github/workflows/stale.yml`)
- ✅ [AGENT] PR coverage comment job (vitest + pytest artifacts; Codecov optional) (`.github/workflows/ci.yml`)
- ✅ [AGENT] `scripts/generate-winget-manifest.sh` stub generator (`packaging/winget/**`, `scripts/`)
- ✅ [AGENT] F-Droid `metadata/` template in `examples/android/` (`examples/android/metadata/**`)
- ✅ [AGENT] Per-stack SBOM slices on GitHub Release (`examples/web`, `examples/python`) (`.github/workflows/release.yml`)
- ✅ [AGENT] PROMPT_LIBRARY Entry 15 — Post-release regression (`PROMPT_LIBRARY.md`)
- ✅ [AGENT] PROMPT_LIBRARY Entry 16 — Template upgrade simulation (`PROMPT_LIBRARY.md`)
- ✅ [AGENT] Issue template: auto-suggest `.template-version` in placeholder text (`.github/ISSUE_TEMPLATE/*.yml`)

## Sprint M3 — Ecosystem Expansion v0.5.0+

- ✅ [AGENT] Add `examples/lightroom/` minimal stub (`Info.lua`, SDK version doc) per `modules/lightroom/MODULE.md`
- ✅ [AGENT] Update `TEMPLATE_INDEX.json` — set `examples/lightroom` module `example` path
- ✅ [AGENT] (Optional) Add `modules/rust/MODULE.md` + `examples/rust/` stub behind stack picker
- ✅ [AGENT] (Optional) Add `modules/go/MODULE.md` + `examples/go/` stub behind stack picker
- ✅ [AGENT] Gate new module CI behind workflow matrix `inputs.stack` or path filters to control CI minutes

## Sprint M4 — Design System v0.6.0

- ✅ [AGENT] Add `design-tokens/` + schema + `scripts/sync-design-tokens.py`
- ✅ [AGENT] Migrate Android example to Compose M3 + theme toggle (DataStore) + `strings.xml` i18n
- ✅ [AGENT] Refactor web example: CSS variables + theme toggle + `locales/` i18n scaffold
- ✅ [AGENT] Add `docs/DESIGN_GUIDE.md` + `.cursor/rules/design-system.mdc`
- ✅ [AGENT] Add `scripts/check-design-cohesion.sh` + validate-bootstrap wiring
- ✅ [AUTO] `android-build` + web tests green (theme toggle smoke tests)
- ✅ [AGENT] Web theme + i18n unit tests (`examples/web/src/theme.test.ts`, `examples/web/src/i18n/**`)
- ✅ [AGENT] Android Compose theme components (`examples/android/.../ui/**`)

## Milestone Gates

- ✅ [AUTO] Workflow action refs validated (`scripts/validate-workflow-actions.sh`)
- ✅ [AUTO] Pre-commit bare-semver guard (`scripts/check-workflow-action-ref-format.sh`)
- ✅ [AUTO] Android assembleDebug CI smoke on `examples/android/`
- ✅ [AUTO] Weekly health-check workflow polls CI + Security Scan + CodeQL
- ✅ [AUTO] UTF-8 encoding check clean (`scripts/check-file-encoding.sh`)
- ✅ [AUTO] Lockfiles present and CI uses locked installs (`npm ci`, `uv sync --locked`)
- ✅ [AUTO] `TEMPLATE_INDEX.json` complete (`scripts/validate-template-index.sh`)
- ✅ [AUTO] Gitleaks CI job passes on `main` (M0)
- ✅ [AUTO] Pre-commit includes file-limits and quick bootstrap validation (M0)
- ✅ [AUTO] Android `assembleRelease` with `SOURCE_DATE_EPOCH` passes (M1)
- ✅ [AUTO] Python coverage ≥ 90% in CI (M1)
- ✅ [AUTO] Web bundle size budget within threshold (M1)
- ✅ [AUTO] OpenSSF Scorecard run completed within last 30 days (M1)
- ✅ [AUTO] Upgrade simulation test passes (M2)
- ✅ [AUTO] GitHub Pages demo deploys successfully (M2)
- ✅ [AUTO] Node example CI green when `examples/node/` present (M2)
## BUILD_PLAN Automation Pass (2026-06-13)

### Sprint 0 — Template (maintainer repo complete)

- ✅ [AGENT] Create `SECURITY.md`, `CODE_OF_CONDUCT.md`, `docs/THREAT_MODEL.md`, `docs/PRIVACY.md`, `docs/RUNBOOK.md`
- ✅ [AGENT] Add `.github/CODEOWNERS` and `THIRD_PARTY_LICENSES.md`
- ✅ [AGENT] Initialize workspace memory files from template seeds (`AGENT_MEMORY.md`, etc.)
- ✅ [AGENT] Wire update checker config into devcontainer and README
- ✅ [HUMAN] Set GitHub repo About description from `docs/GITHUB_ABOUT.md` (via `gh repo edit`)
- ✅ [AGENT] Commit lockfiles (`package-lock.json`, `uv.lock`) and `.env.example`
- ✅ [AGENT] Ensure `TEMPLATE_INDEX.json` includes all scripts, workflows, and playbooks
- ✅ [AUTO] `scripts/check-file-encoding.sh` passes
- ✅ [AUTO] Full Build Verification Gate (INITIALIZATION_PROMPT Section 7) green
- ✅ [AUTO] `scripts/validate-bootstrap.sh` (expanded) passes in CI
- ✅ [HUMAN] Enable Dependabot alerts + security updates
- ✅ [HUMAN] Enable private vulnerability reporting + branch protection on `main` (via `setup-github-repo.sh`)
- ✅ [HUMAN] Replace `@[PROJECT_OWNER]` in CODEOWNERS with `@edwardlthompson`

### Sprint 0 Parallel (maintainer)

- ✅ [AGENT] Confirm GitHub Pages uses Actions (not `/docs` folder)
- ✅ [AUTO] Verify pre-commit hooks install

### Sprint 1 — Golden Path (maintainer)

- ✅ [AGENT] Propose directory structure for target stack
- ✅ [AGENT] Draft ADR-0001 core architecture (`docs/adr/0001-core-architecture.md`)
- ✅ [AGENT] Implement Golden Path reference feature (design tokens, i18n, theme toggle)
- ✅ [AUTO] `scripts/check-design-cohesion.sh` passes
- ✅ [AUTO] CI matrix green on main
- ✅ [AGENT] Web PWA offline cache + bundle budget + visual snapshots
- ✅ [AGENT] Python CLI + 90% coverage gate + pyright
- ✅ [AGENT] Android FOSS skeleton + Fastlane metadata stub
- ✅ [AGENT] Node API stub
- ✅ [AGENT] CodeQL + Trivy workflow wiring
- ✅ [AGENT] Devcontainer + pre-commit hooks

### Sprint M0 Parallel

- ✅ [AGENT] Cross-platform `scripts/check-file-encoding.py` (UTF-8/UTF-16 BOM)
- ✅ [AGENT] Add `.cursor/rules/windows-encoding.mdc`
- ✅ [AGENT] Add PROMPT_LIBRARY Entry 10 — Pre-release gate
- ✅ [AGENT] Add PROMPT_LIBRARY Entry 11 — GitHub repo setup
- ✅ [AGENT] Document setup script in `docs/SECURITY_TRIAGE.md` § Setup
- ✅ [AGENT] Wire `setup-github-repo` reminder into `init-project.sh` / `.ps1`
- ✅ [AUTO] Full Build Verification Gate + `scripts/pre-release-gate.sh` green on `main`

### Sprint M1 Parallel

- ✅ [AGENT] Web bundle size budget in CI (`scripts/check-bundle-size.sh`)
- ✅ [AGENT] Playwright visual snapshot regression test
- ✅ [AGENT] Service-worker offline smoke test
- ✅ [AGENT] Android Fastlane metadata stub
- ✅ [AGENT] Android emulator checklist in `examples/android/README.md`
- ✅ [AGENT] Optional pyright CI job for Python
- ✅ [AGENT] Add `.cursor/rules/testing.mdc` (coverage budgets)
- ✅ [AGENT] Add `.cursor/rules/ci-gates.mdc` (post-push poll protocol)
- ✅ [AGENT] PROMPT_LIBRARY Entry 12 — Stack prune complete
- ✅ [AGENT] PROMPT_LIBRARY Entry 13 — Session state restore
- ✅ [AGENT] PROMPT_LIBRARY Entry 14 — Parallel agent scope map
- ✅ [AGENT] OpenSSF Scorecard weekly workflow
- ✅ [AGENT] `scripts/check-parallel-scope.sh`
- ✅ [AUTO] CI matrix green including `android-release` and coverage gate
- ✅ [AGENT] Conventional Commits PR title check (`amannn/action-semantic-pull-request`)

### Sprint M3 Parallel

- ✅ [HUMAN] Decide which optional modules to ship — all three (Lightroom, Rust, Go); see `DECISION_LOG.md`
- ✅ [AGENT] Lightroom lint/checklist in CI (Lua SDK namespace grep)
- ✅ [AGENT] Rust CI job (`cargo fmt`, `clippy`, `test`)
- ✅ [AGENT] Go CI job (`go vet`, `gofmt`, `test`)
- ✅ [AGENT] F-Droid submission dry-run checklist doc (`modules/android/MODULE.md`)

### Milestone Gates

- ✅ [AUTO] Regression tests: zero failures
- ✅ [AUTO] Static analysis and vulnerability scans clean
- ✅ [AUTO] `scripts/pre-release-gate.sh` passes before release tag (M0)

## Sprint M7 — Incremental Feature Assembly + Agent Gates (2026-06-15)

- ✅ [AGENT] Add `docs/FEATURE_MODULES.md` and `.cursor/rules/feature-modules.mdc`
- ✅ [AGENT] Add `feature-gate.sh`, `feature-autofix.sh`, `agent-progress.sh`, `watch-agent-gates.sh`, `smoke-stack.sh` (+ `.ps1`)
- ✅ [AGENT] Extend session-state example, `ci-gates.mdc`, `testing.mdc`, `destructive-ops.mdc`; gitignore `agent-progress.json`
- ✅ [AGENT] Update BUILD_PLAN Sprint 2+ template, INITIALIZATION_PROMPT, FOR_AGENTS, PROMPT_LIBRARY Entry 17
- ✅ [AGENT] Harden agent handoff: `gates_passed`, `failed_stage`, `log_tail` in `agent-progress.sh`; `--step` forwarding
- ✅ [AGENT] Fix `watch-agent-gates.sh` JSON capture; scoped `--paths` autofix; `GATES_PASSED` subshell fix
- ✅ [AGENT] Add `FEATURE_MODULES.md` to `validate-bootstrap.sh`; cross-link `START_HERE.md`; node MODULE Feature gate section
- ✅ [AGENT] Integrate M7 closeout + Sprint M8 block into BUILD_PLAN.md

## Sprint M8 — Feature Gate CI Enforcement (2026-06-15)

- ✅ [AGENT] CI **Feature Gate** job with `--strict` multi-stack
- ✅ [AGENT] `pre-release-gate.sh` runs `feature-gate.sh`
- ✅ [AUTO] Branch protection includes Repo Hygiene + Feature Gate via `setup-github-repo.sh`
- ✅ [AUTO] `verify-about-feature-gate.sh`, `check-security-triage.sh`, `check-readme-health.sh`
- ✅ [AUTO] CI green on `810e259`; BUILD_PLAN HUMAN rows re-labeled to AGENT/AUTO where automatable

## Sprint M6 — Repo Hygiene Automation (2026-06-15)

- ✅ [AGENT] Add `.gitattributes`, `.editorconfig`, `.cursorignore`; expand `.gitignore`
- ✅ [AGENT] Add `check-tracked-artifacts`, `check-large-tracked-files`, `check-repo-hygiene`, `purge-ephemeral` scripts (+ `.ps1`)
- ✅ [AGENT] Wire repo-hygiene into pre-commit, `validate-bootstrap.sh`, and CI `repo-hygiene` job
- ✅ [AGENT] Add `docs/REPO_HYGIENE.md` and `.cursor/rules/repo-hygiene.mdc`
- ✅ [AUTO] CI **Repo Hygiene** job green after merge
- ✅ [AGENT] Archive Sprint M6 completions to `COMPLETED_TASKS.md`
- ✅ [AGENT] Index hygiene `.ps1` twins in `TEMPLATE_INDEX.json`

## Maintainer gate cycle (2026-06-15)

- ✅ [AUTO] `check-security-triage.sh --wait-ci 120` — zero Critical/High Dependabot; CI + Security Scan + CodeQL green on `f3013a0`
- ✅ [AUTO] `pre-release-gate.sh` — feature-gate, CI, Dependabot, `.template-version` 0.7.1
- ✅ [AUTO] `simulate-template-upgrade.sh` passed
- ✅ [AUTO] `run-maintainer-gates.sh --quick` — readme, fdroid metadata, feature-gate, CI jobs Repo Hygiene + Feature Gate
- ✅ [AUTO] `check-license-compliance.sh web` passed
- ✅ [AGENT] Fix Scorecard workflow job-level permissions (was failing publish_results)
- ✅ [AGENT] Add `docs/features/_template.md`, `docs/features/settings.md`, `verify-fdroid-metadata.sh`, `run-maintainer-gates.sh`
- ✅ [AGENT] F-Droid metadata scaffold: changelogs/1.txt, images/README.md
- ✅ [AUTO] Release Please PR #11 open (`chore(main): release 0.8.0`); pre-release gate green on `main`

## Sprint 2 starter scaffold (template maintainer, 2026-06-15)

- ✅ [AGENT] Feature acceptance template + Settings feature draft in `docs/features/`
- ✅ [AGENT] About screen remains Sprint 1 reference exemplar (not duplicated as Sprint 2 feature)
- ✅ [AGENT] BUILD_PLAN Sprint 2+ feature template rows indexed for child repos

## BUILD_PLAN cleanup (2026-06-15)

- ✅ [AGENT] Archive completed M5–M8 sprints; remove stale `✅` rows from active board
- ✅ [AGENT] Consolidate milestone gates into recurring pre-release + `run-maintainer-gates.sh`
- ✅ [AGENT] Split child-repo playbook from template-maintainer open items

## Code review → Sprint M9 integration (2026-06-15)

- ✅ [AGENT] Integrate 46 code-review findings into BUILD_PLAN Sprint M9 (Sequential + Parallel + Critique)
- ✅ [AGENT] Update PARALLEL_AGENT_SCOPES.md with M9 active scopes
- ✅ [AGENT] Reconcile child-repo Sprint 0 sign-off; simplify per-feature checklist; restore lane structure

## Sprint M9 — Sequential 1–7 (2026-06-15)

- ✅ [HUMAN/AGENT] Commit maintainer artifacts; scorecard fix; feature docs; metadata scaffold
- ✅ [AGENT] Fix 3-strike logic; `verify-agent-strikes.sh`
- ✅ [AGENT] `agent-progress.sh next --lane maintainer`; default `--step gate`
- ✅ [AGENT] `feature-gate.sh`: file-limits, python mypy/pyright; CI-only web gates documented
- ✅ [AGENT] Paginated Dependabot; `pre-release-gate` in `release.yml` workflow_dispatch
- ✅ [AGENT] TEMPLATE_INDEX bulk index + reverse validate-template-index scan
- ✅ [AGENT] About exemplar: AppShell refactor, Android UpdateStatusEvaluator, expanded about unit tests

## Sprint M9 — Sequential 8–12 + Parallel A–D (2026-06-15)

- ✅ [AGENT] Settings vertical slice per `docs/features/settings.md` (web + android containers, tests, i18n)
- ✅ [AGENT] Extend `check-file-limits.sh` for `.kt` Compose + `components/*.ts`; node in `init-project` stack picker
- ✅ [AGENT] Reconcile Sprint 0 sign-off across BUILD_PLAN, `INITIALIZATION_PROMPT.md`, `read-before-write.mdc`
- ✅ [AGENT] Scorecard in `check-security-triage.sh`; update `SECURITY.md`, `MAINTAINING_THE_TEMPLATE.md`, `START_HERE.md`, `FEATURE_MODULES.md`
- ✅ [AGENT] Module E/F renumbering; ADR-0000 template baseline; `security-triage.mdc`
- ✅ [AGENT] Parallel A: web settings slice + e2e smoke
- ✅ [AGENT] Parallel B: android settings slice + tests
- ✅ [AGENT] Parallel C: gate/CI hardening (file-limits, Scorecard triage)
- ✅ [AGENT] Parallel D: docs + rules + index (Node column, ADR-0000, security-triage.mdc)
- ✅ [AGENT] F-Droid image paths under `metadata/en-US/images/`; fdroiddata handoff in `modules/android/MODULE.md`

## BUILD_PLAN cleanup (2026-06-15, M9 closeout)

- ✅ [AGENT] Archive completed M9 AGENT rows; slim active board to release + distribution open items

## Sprint M11 — Post-M10 hardening (AGENT, 2026-06-15)

- ✅ [AGENT] Fix Android compile errors (`MainActivity` launch import; `GoldenPathApp` scope.launch)
- ✅ [AGENT] CodeQL java-kotlin: setup-java, Android SDK, Gradle assembleDebug before analyze
- ✅ [AGENT] ReleaseTagFetcher on Dispatchers.IO; offline + CheckSchedule gating; ReleaseAssetSelector wired
- ✅ [AGENT] release.yml: full pre-release on workflow_dispatch; lightweight tag gate (version + CI snapshot)
- ✅ [AGENT] Robolectric DataStore tests: ThemePreferencesTest, AppUpdatePreferencesTest
- ✅ [AGENT] About parity: clickable donations, no_compatible string, header nav toggle, BuildConfig.VERSION_NAME
- ✅ [AGENT] Web appBootstrap.ts composition root; settings.md wiring map updated
- ✅ [AGENT] Gate dedupe: run-maintainer-gates full mode uses pre-release only; check-github-ci --jobs
- ✅ [AGENT] Prune stale about.update.interval.* i18n; web e2e for update-check + About panel

## Sprint M12 — Post-M11 polish (AGENT, 2026-06-15)

- ✅ [AGENT] CodeQL Android: init before Gradle traced build
- ✅ [AGENT] Tag release gate `--wait 300 --jobs "Repo Hygiene,Feature Gate"`; `check-github-ci.ps1` `-Jobs`
- ✅ [AGENT] Robolectric DataStore isolation + `pendingRestart` test
- ✅ [AGENT] `ReleaseTagFetcherTest`, `DonationsLoaderTest`, `MainActivitySmokeTest`
- ✅ [AGENT] Web `appBootstrap.ts` vitest coverage + smoke tests
- ✅ [AGENT] Android `pendingRestart` UI stub in `GoldenPathApp`; DESIGN_GUIDE parity note
- ✅ [AGENT] Composition-root docs (`FEATURE_MODULES.md`, `feature-modules.mdc`, BUILD_PLAN Sprint 2)
- ✅ [AGENT] CHANGELOG M10/M11/M12; exemplar vs `.template-version` in MAINTAINING_THE_TEMPLATE; bug_report placeholder
- ✅ [AUTO] CodeQL workflow green on `main` after push (`7055255`)
- ✅ [HUMAN] Merge Release Please PR #11 after CodeQL + branch-protection checks green

## v0.9.0 release (2026-06-15)

- ✅ [HUMAN] Approve release tag; merge Release Please PR #12 (`chore(main): release 0.9.0`, `fd699bc`)
- ✅ [AUTO] Release Please published [v0.9.0](https://github.com/edwardlthompson/agent-project-bootstrap/releases/tag/v0.9.0)
- ✅ [AUTO] CI + Feature Gate + CodeQL green on `main` after merge (`fd699bc`)

## v0.8.0 release (2026-06-15)

- ✅ [HUMAN] Merge Release Please PR #11 (`chore(main): release 0.8.0`, `10b46d6`)
- ✅ [AUTO] CI + Feature Gate + CodeQL green on `main` after M12 (`7055255`)

## BUILD_PLAN cleanup (2026-06-15, M12 + v0.8.0 closeout)

- ✅ [AGENT] Archive M12 sprint body; slim active board to distribution + maintainer open items
- ✅ [AGENT] Unicode task markers (`🔲` / `✅` / `❌`) across BUILD_PLAN and checklist docs

## Sprint M13 — Human-gate automation (AGENT, 2026-06-15)

- ✅ [AGENT] `verify-branch-protection.sh` / `.ps1` — gh API compare vs `setup-github-repo.sh` defaults
- ✅ [AGENT] `init-project.sh` / `.ps1` `--stack`, `--prune`, and related CLI flags
- ✅ [AGENT] `verify-reproducible-apk.sh` / `.ps1` — local double-build hash check (CI parity)
- ✅ [AGENT] Wire branch-protection into `run-maintainer-gates.sh`; `TEMPLATE_INDEX.json` entries
- ✅ [AUTO] `verify-branch-protection.sh` green on template repo `main`

## Sprint M14 — Post-M13 review remediation (AGENT, 2026-06-15)

- ✅ [AGENT] P0 version coherence: `.template-version`, `TEMPLATE_INDEX.json`, `AGENT_MEMORY.md` → 0.8.0; manifest assert in `pre-release-gate.sh`
- ✅ [AGENT] P0 `init-project.ps1` `2>$null` fix; `-NonInteractive` + Python placeholder replacement in both init scripts
- ✅ [AGENT] P1 `run-maintainer-gates.sh`: `verify-reproducible-apk.sh` wiring, `--skip-apk`, unknown-flag fail, `--quick` docs
- ✅ [AGENT] P1 `verify-branch-protection.sh`: `strict` + `allow_force_pushes` asserts; rulesets note in `SECURITY_TRIAGE.md`
- ✅ [AGENT] P1 docs: `settings.md` in `TEMPLATE_INDEX.json`; reconcile `CHANGELOG.md` `[Unreleased]`; init CLI in `INITIALIZATION_PROMPT.md` §8
- ✅ [AGENT] P1 web: `AboutPanel.ts` DOM-safe donations; `APP_VERSION` via Vite `define`
- ✅ [AGENT] P1 Android: `check-file-limits.sh` GoldenPath UI roots; home-screen update status banner
- ✅ [AGENT] P1 CI: Android SBOM in `release.yml`; tag vs `workflow_dispatch` gate docs
- ✅ [AUTO] CI + Feature Gate green on `main` (`fc71433`)
- ✅ [HUMAN] Close stale M5 visual-review row (superseded by maintainer README cycles)
- ✅ [AGENT] Init next-steps numbering fixed in `.sh` / `.ps1`

## Sprint M15 — P2 backlog (AGENT, 2026-06-15)

- ✅ [AGENT] Init `--keep-optional` / `--prune-optional` for rust/go/lightroom when pruning
- ✅ [AGENT] CodeQL rust/go exclusion documented in `codeql.yml` + `modules/rust|go/MODULE.md`
- ✅ [AGENT] Playwright e2e: update check enabled → About status assertion
- ✅ [AGENT] `simulate-template-upgrade.sh` non-interactive init smoke
- ✅ [AGENT] `MainActivitySmokeTest` migrated to `ActivityScenarioRule`
- ✅ [AUTO] CI + Feature Gate green on `main` (`a5f3199`)
- ✅ [AGENT] `connectedDebugAndroidTest` CI job (`android-instrumented`); documented in `modules/android/MODULE.md`
- ✅ [AGENT] `release.yml` SBOM upload on `release` published + Release Please dispatch; tag push gate-only split
- ✅ [AUTO] CI + Feature Gate green on `main` (`5195c46`)
- ✅ [AGENT] SBOM backfill for v0.9.0; dispatch skip pre-release gate when `tag` input set

## Sprint M16 — Post-M15 code review (AGENT, 2026-06-15)

- ✅ [AGENT] P0 `--skip-workflows` on `check-github-ci.sh` / `.ps1`; tag-gate jobs-only poll in `release.yml`
- ✅ [AGENT] P0 SBOM tag ↔ `.template-version` assert; single checkout in `sbom-assets`
- ✅ [AGENT] P1 docs: `SECURITY_TRIAGE.md`, `MAINTAINING_THE_TEMPLATE.md`, `OPTIONAL_STACKS.md`
- ✅ [AGENT] P1 CI `path-changes` job; AOSP emulator target; `upgrade-simulation` gate enforced
- ✅ [AGENT] P1 BOM-less JSON writes in `init-project.ps1`; Playwright mocked update e2e
- ✅ [AGENT] P1 Release Please SBOM dedupe (`release` published only)
- ✅ [AUTO] CI + Feature Gate green on `main` (`f7213ec`, `7846d96`)
- ✅ [AGENT] P2 `--prune-optional` smoke in `simulate-template-upgrade.sh`; init flags docs
- ✅ [AGENT] P2 `AboutPanel` `aria-live="polite"`; `appBootstrap.test.ts` en.json strings
- ✅ [AGENT] Fix `examples/lightroom` removal on `--prune-optional` in init scripts

## Sprint M17 — Post-M16 code review (AGENT, 2026-06-15)

- ✅ [AGENT] P0 Android INTERNET permission + `ReleaseTagFetcherTest` (manifest + invalid-repo fetch)
- ✅ [AGENT] P0 Web update timing: `lastChecked` after successful fetch; unit tests for failure retry
- ✅ [AGENT] P0 Prune + template index: `init-stack-sync.py` prune index; simulate post-prune asserts
- ✅ [AGENT] P0 Release SBOM gate: `check-github-ci.sh --wait` on `release` published before SBOM
- ✅ [AGENT] P1 `check-github-ci.ps1` in-progress WAIT parity; `health-check.yml` `--wait 600`
- ✅ [AGENT] P1 `init-stack-sync`: emoji sync, rust/go MODULE_LINES, multi+prune `pruned` fix
- ✅ [AGENT] P1 Docs drift: INITIALIZATION_PROMPT step 5, Node in OPTIONAL_STACKS/README
- ✅ [AGENT] P1 FOSS grep: Kotlin/manifest/XML in `ci.yml`; path-changes android triggers
- ✅ [AGENT] P1 Pre-release: `check-license-compliance.sh`; manifest missing = FAIL
- ✅ [AGENT] Fix prune regression: `sync-design-tokens.py` + design cohesion stack-aware checks
- ✅ [AUTO] CI + Feature Gate green on `main` (`5d9be3e`)

## M17 P2 backlog (AGENT, 2026-06-15)

- ✅ [AGENT] Web modal a11y: `role="dialog"`, `aria-modal`, focus trap, Escape (`panelDialog.ts`)
- ✅ [AGENT] Wire `applyPwaUpdate()` in About panel; network-first SW; `UpdateApplierTest` for Android install boundary
- ✅ [AGENT] Config `.example` for web public + Android assets; stub `release_repo` in template
- ✅ [AGENT] `init-project.ps1` smoke in `simulate-template-upgrade.sh`; `ReleaseRepo` `Test-Path` guard
- ✅ [AGENT] Module letters E–G; `node` in `PARALLEL_AGENT_SCOPES.md`; index `MAINTAINING_THE_TEMPLATE.md`
- ✅ [AGENT] Android `GoldenPathUiTest` instrumented settings/about/theme assertions
- ✅ [AGENT] `checkForUpdates()` unit tests + axe e2e on open panels
- ✅ [AGENT] `android-release` CI strict reproducibility; rust/go SBOM slices in `release.yml`
- ✅ [AGENT] `health-check.yml` `uv sync --all-extras` for pip audit parity

## Sprint M18 — Post-P2 code review (AGENT, 2026-06-16)

- ✅ [AGENT] P0 Pages base path: `assetUrl()` helper; relative SW precache; BASE_URL-aware fetch/register
- ✅ [AGENT] P0 Web first paint: immediate `render()` in `appBootstrap.ts`; background update re-renders
- ✅ [AGENT] P0 Android apply slice: `ApkDownloadHelper`, `UpdateApplyCoordinator`, Apply button in About/home
- ✅ [AGENT] P0 Init config propagation: `sync-stack-config.py` wired in init scripts
- ✅ [AGENT] P1 Release SBOM guards: `hashFiles` conditionals for web/python/node/android; conditional upload
- ✅ [AGENT] P1 `init-stack-sync`: `active_modules` derived from filesystem via `MODULE_EXAMPLE_DIRS`
- ✅ [AGENT] P1 Release tag gate: full required-check poll on tag push
- ✅ [AGENT] P1 Repo hygiene: live config JSON gitignored; `sync-exemplar-config.sh`; tracked-artifact check
- ✅ [AGENT] P1 Go example: `go mod tidy` in CI; SBOM gated on `go.sum` (N/A for zero-dep stub)
- ✅ [AUTO] CI + Feature Gate green on `main` (`2721c01`)

## M18 P2 backlog (AGENT, 2026-06-16)

- ✅ [AGENT] `panelDialog.ts` unit tests (focus trap, Escape, focus restore)
- ✅ [AGENT] Playwright e2e for PWA apply + restart guard
- ✅ [AGENT] Web home update banner parity with Android
- ✅ [AGENT] `feature-gate.sh` design cohesion + about gate in strict multi
- ✅ [AGENT] Weekly Android instrumented smoke in `health-check.yml`
- ✅ [AGENT] KB-008 `android-release` strict hash policy documented
- ✅ [AGENT] `health-check.yml` simulate-template-upgrade step
- ✅ [AGENT] `run-maintainer-gates.sh` dedupe feature-gate in full mode
- ✅ [AGENT] `TEMPLATE_INDEX.json` roadmap + key exemplar paths
- ✅ [AGENT] SW `CACHE_NAME` stamped from package version at build
- ✅ [AGENT] `feature-gate.sh` rust/go smoke for multi strict
- ✅ [AGENT] `check-license-compliance.sh` rust/go slices
- ✅ [AUTO] CI + Feature Gate green on `main` (`d6b92a2`)

## Sprint M27 — Batch Instruction Templates (AGENT, 2026-06-17)

Slash commands + bare-word triggers for 25 batch workflows (20 atomic + 5 super).

- ✅ [AGENT] Create `.cursor/commands/*.md` (audit, debug, gates, triage, dependabot, push, prerelease, regress, feature, fix, init, prune, ci, docs, upgrade, setup, plan, restore, compact, scope + bootstrap, verify, build, ship, maintain)
- ✅ [AGENT] Add `.cursor/rules/batch-commands.mdc` (alwaysApply bare-word expansion)
- ✅ [AGENT] `docs/help/BATCH_COMMANDS.md` human cheat sheet; `docs/BATCH_COMMANDS.md` agent registry
- ✅ [AGENT] `CODE_REVIEW.md.example`, `RELEASE_NOTES.md.example`; gitignore ephemeral outputs
- ✅ [AGENT] `scripts/check-batch-commands.sh`; wire `validate-bootstrap.sh`, `simulate-template-upgrade.sh`, `TEMPLATE_INDEX.json`
- ✅ [AGENT] README Agent shortcuts; Child Playbook 2b; PROMPT_LIBRARY Entries 22–46; CURSOR_MODES batch row
- ✅ [AUTO] Validate: bootstrap --quick, template-index, feature-gate, check-batch-commands

## BUILD_PLAN cleanup (2026-06-17, M27 complete)

- ✅ [AGENT] Archive M27; extend Archived Sprints row to M19–M27

## Sprint M26 — Repo Sanity III (AGENT, 2026-06-17)

Post-commit review: TEMPLATE_INDEX drift, START_HERE path consistency, stale archive notes.

- ✅ [AGENT] Add `.cursor/rules/cursor-modes.mdc` to `TEMPLATE_INDEX.json` (bootstrap REQUIRED but unindexed)
- ✅ [AGENT] Align `START_HERE.md` repo-mode bullets with `docs/` paths
- ✅ [AGENT] Resolve stale M25 commit-blocker note in `COMPLETED_TASKS.md`
- ✅ [AUTO] Validate: bootstrap --quick, template-index, feature-gate, simulate-template-upgrade

**Deferred (no action):** CHANGELOG historical mojibake (`ΓÇö`) and legacy semver order — cosmetic; high diff noise.

## BUILD_PLAN cleanup (2026-06-17, M26 complete)

- ✅ [AGENT] Archive M26; extend Archived Sprints row to M19–M26

## Sprint M25 — Repo Sanity II (AGENT, 2026-06-17)

Post-M24 review: markdown table break, CHANGELOG ref, upgrade sim coverage.

- ✅ [AGENT] Fix `MAINTAINING_THE_TEMPLATE.md` table/heading blank line
- ✅ [AGENT] Retarget CHANGELOG historical Section 7 → 7a; extend `UPGRADING_FROM_TEMPLATE.md`
- ✅ [AGENT] Add CURSOR_MODES + changelog check to `simulate-template-upgrade.sh` AREAS
- ✅ [AUTO] Validate: bootstrap --quick, feature-gate (pass); simulate green after commit `9782e75`

## BUILD_PLAN cleanup (2026-06-17, M25 complete)

- ✅ [AGENT] Archive M25; extend Archived Sprints row to M19–M25

## Sprint M24 — Repo Sanity (AGENT, 2026-06-17)

Full-repo review: duplicate CHANGELOG [Unreleased], regression gate, init prompt sync.

- ✅ [AGENT] Remove duplicate CHANGELOG [Unreleased]; relocate M5 bullets to [0.5.0]
- ✅ [AGENT] Add `scripts/check-changelog-unreleased.sh`; wire validate-bootstrap + TEMPLATE_INDEX
- ✅ [AGENT] Sync INITIALIZATION_PROMPT §8 step 17 with CURSOR_MODES cross-link
- ✅ [AUTO] Validate: encoding, template-index, bootstrap --quick, feature-gate

**Deferred (no action):** CHANGELOG legacy semver order (0.5.0 before 0.2.2) and historical mojibake — cosmetic; batch normalize risks Release Please diffs.

## BUILD_PLAN cleanup (2026-06-17, M24 complete)

- ✅ [AGENT] Archive M24; extend Archived Sprints row to M19–M24

## Sprint M23 — Cursor Mode Closure (AGENT, 2026-06-17)

Upgrade guide, bootstrap gate for rule file, Debug links on gate failures, CHANGELOG.

- ✅ [AGENT] Add CURSOR_MODES + cursor-modes.mdc to UPGRADING_FROM_TEMPLATE cherry-pick table
- ✅ [AGENT] Link gate exit 2 / Failure Playbook to Debug Mode in feature-modules.mdc and FOR_AGENTS
- ✅ [AGENT] Add `.cursor/rules/cursor-modes.mdc` to validate-bootstrap.sh REQUIRED
- ✅ [AGENT] Document M19–M22 in CHANGELOG [Unreleased]; devcontainer CURSOR_MODES tip
- ✅ [AUTO] Validate: encoding, template-index, bootstrap --quick

## BUILD_PLAN cleanup (2026-06-17, M23 complete)

- ✅ [AGENT] Archive M23; extend Archived Sprints row to M19–M23

## Sprint M22 — Cursor Mode Consistency (AGENT, 2026-06-17)

Final pass: §7a reference drift, child playbook, session-restore prompts, maintainer safe-edit table.

- ✅ [AGENT] Retarget stale "Section 7" refs → §7a in INITIALIZATION_PROMPT, SECURITY_TRIAGE, THIRD_PARTY_LICENSES
- ✅ [AGENT] Align START_HERE repo-mode bullets + Child Playbook Sprint 0 step 2a with CURSOR_MODES
- ✅ [AGENT] Clarify repo vs Cursor mode in FOR_AGENTS Session Checkpoint + PROMPT_LIBRARY Entry 13
- ✅ [AGENT] Add CURSOR_MODES to MAINTAINING_THE_TEMPLATE safe-edit table; init step 2 README link
- ✅ [AGENT] Link 3-strike escalation to Debug Mode in FOR_AGENTS
- ✅ [AUTO] Validate: encoding, template-index, bootstrap --quick

## BUILD_PLAN cleanup (2026-06-17, M22 complete)

- ✅ [AGENT] Archive M22; consolidate M19–M22 in Archived Sprints table

## Sprint M21 — Cursor Mode Drift (AGENT, 2026-06-17)

Post-M20 review: init scripts, startup sequence, contributor docs, session-state schema, index entry_points.

- ✅ [AGENT] Sync `init-project.sh` / `init-project.ps1` next-steps prompt with CURSOR_MODES
- ✅ [AGENT] Add Cursor mode pick to `INITIALIZATION_PROMPT.md` §8 Startup Sequence (step 1a)
- ✅ [AGENT] Cross-link `docs/FEATURE_MODULES.md` and `CONTRIBUTING.md` to `docs/CURSOR_MODES.md`
- ✅ [AGENT] Clarify `.cursor-session-state.example.json` `mode` = repo mode; add `cursor_modes` to `TEMPLATE_INDEX.json` entry_points
- ✅ [AGENT] Align `core-directives.mdc` session-start line; note `cursor-modes.mdc` in README Cursor rules
- ✅ [AUTO] Validate: encoding, template-index, bootstrap --quick

## BUILD_PLAN cleanup (2026-06-17, M21 complete)

- ✅ [AGENT] Archive M21 sprint body; slim board to maintenance + human open items

## Sprint M20 — Cursor Mode Wiring (AGENT, 2026-06-17)

Post-M19 review: close prompt/read-order gaps and enforce CURSOR_MODES in bootstrap gate.

- ✅ [AGENT] Sync `START_HERE.md` agent prompts + Reference read order with `docs/CURSOR_MODES.md`
- ✅ [AGENT] Sync `PROMPT_LIBRARY.md` Entry 1/2 and `README.md` Quick Start bootstrap prompt
- ✅ [AGENT] Dedupe `INITIALIZATION_PROMPT.md` §6 Plan First → pointer to `docs/CURSOR_MODES.md`
- ✅ [AGENT] Update `AGENTS.md` Session Protocol; add `docs/CURSOR_MODES.md` to `validate-bootstrap.sh` REQUIRED
- ✅ [AGENT] Add `docs/CURSOR_MODES.md` to README What's Included; fix KB range in START_HERE
- ✅ [AUTO] Validate: encoding, template-index, bootstrap --quick

## BUILD_PLAN cleanup (2026-06-17, M20 complete)

- ✅ [AGENT] Archive M20 sprint body; slim board to maintenance + human open items

## Sprint M19 — Cursor Mode Routing (AGENT, 2026-06-17)

- ✅ [AGENT] Create `docs/CURSOR_MODES.md` (mode table, trivial rubric, transitions, prompt shortcuts; ≤80 lines)
- ✅ [AGENT] Create `.cursor/rules/cursor-modes.mdc` (`alwaysApply: true`; ≤30 lines; pointer to CURSOR_MODES)
- ✅ [AGENT] Wire entry points: `START_HERE.md`, `AGENTS.md`, `FOR_AGENTS.md`, `core-directives.mdc`, `TEMPLATE_INDEX.json`
- ✅ [AGENT] Split `INITIALIZATION_PROMPT.md` §7a (pre-release audit, Agent) vs §7b (defect investigation, Debug)
- ✅ [AGENT] Update `PROMPT_LIBRARY.md`: retitle Entry 3; add Entries 18–21 (Ask/Plan/Debug/Agent)
- ✅ [AUTO] Validate: `check-file-encoding.py`, `validate-template-index.sh`, `validate-bootstrap.sh --quick`

## BUILD_PLAN cleanup (2026-06-17, M19 complete)

- ✅ [AGENT] Archive M19 sprint body; slim board to maintenance + human open items

## BUILD_PLAN cleanup (2026-06-16, M18 P2 complete)

- ✅ [AGENT] Archive M18 sprint body; slim board to maintenance + human open items

## BUILD_PLAN cleanup (2026-06-16, M18 complete)

- ✅ [AGENT] Archive M18 sequential; slim board to P2 backlog + human open items

## BUILD_PLAN cleanup (2026-06-15, M17 P2 complete)

- ✅ [AGENT] P2 backlog: modal a11y, PWA apply wiring, config `.example`, PS1 smoke, docs/index, Android UI tests, release SBOM/reproducibility

## BUILD_PLAN cleanup (2026-06-15, M17 complete)

- ✅ [AGENT] Archive M17 sprint body; slim board to P2 backlog + human open items

## BUILD_PLAN cleanup (2026-06-15, M16 complete)

- ✅ [AGENT] Archive M16 sprint body; slim board to maintenance + human open items

## BUILD_PLAN cleanup (2026-06-15, M15 complete)

- ✅ [AGENT] Archive M15 sprint body; slim board to maintenance + human open items

## BUILD_PLAN cleanup (2026-06-15, M14 + v0.9.0 archive)

- ✅ [AGENT] Archive M14 sprint body; promote P2 to Sprint M15 active board
- ✅ [AGENT] Reset pre-release checklist for next version cycle

## Sprint M10 — Code review remediation (AGENT, 2026-06-15)

- ✅ [AGENT] M9-8 settings slice + parallel A–D committed; BUILD_PLAN cleanup
- ✅ [AGENT] Branch protection: export `GITHUB_REQUIRED_CHECKS` in `setup-github-repo.sh`; docs sync (5 checks)
- ✅ [AGENT] Node stack init: prune paths, `init-stack-sync.py` MODULE_LINES + PARALLEL_NOTES, INITIALIZATION_PROMPT Node row
- ✅ [AGENT] `check-security-triage.sh --strict`; Scorecard in `pre-release-gate.sh`; `SECURITY_TRIAGE.md` Scorecard section
- ✅ [AGENT] Gate parity: `--strict` in pre-release/maintainer gates; `pre-release-gate.sh` on tag push in `release.yml`
- ✅ [AGENT] Web settings fidelity: i18n, CSS, vitest coverage, cold-restart e2e, theme toggle sync
- ✅ [AGENT] Android settings fidelity: theme FilterChips, innerPadding, CheckSchedule tests
- ✅ [AGENT] Android About parity: DonationsLoader, ReleaseTagFetcher, GoldenPathApp composition root
- ✅ [AGENT] Opt-in update checks default `off`; About interval UI removed (Settings toggle only)
- ✅ [AGENT] CI/release: CodeQL java-kotlin, node SBOM + health-check audit

