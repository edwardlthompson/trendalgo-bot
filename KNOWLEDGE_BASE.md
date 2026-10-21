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

## KB-012 — v0.2.0 ship CI follow-ups (2026-06-26)

**Symptom:** `/ship` pushed DEX S21–S24 + exchange S19–S20 to `main`; CI green blocked on mypy (~80 legacy errors), Playwright axe (color-contrast on portfolio heatmap/tags), offline SW e2e flaky with route mocks.

**Fix:** Commits `99557b1`–`37fdecb` on `main` (release + uv.lock + e2e mocks + heatmap contrast). Re-run `bash scripts/check-github-ci.sh --wait 600`. Remaining: mypy strict debt (pre-existing), axe audit on default portfolio view, service-worker offline test. Trigger Release Please / tag `v0.2.0` after CI green. Human gates H-032/H-035/H-036 still open.

## KB-013 — R-Audit-5 CI green (2026-06-26)

**Symptom:** `/audit` R-Audit-5; CI red on Playwright axe (timeline range label, portfolio load), flaky SW offline navigation e2e; WSL absent on Windows founder machine.

**Fix:** R-Audit-5 — `TimelineScrubber` `aria-label`/`aria-valuetext`; heatmap opacity removed; accent swatch labels; e2e waits for `portfolio-panel`; offline test uses `offline` event (SW unit-tested in Vitest); `sw.js` skips `/api/` interception. Windows gates: `python scripts/run-trendalgo-tests.py`, `check_risk_mitigations.py`. Enable Dependabot in GitHub Settings (F-053). Push → `bash scripts/check-github-ci.sh --wait 600` for v0.2.0 tag.

## KB-019 — Windows EXE/MSI release assets (2026-10-20)

**Symptom:** `/ship` / `release.yml` uploaded only SBOMs; no `TrendAlgo-X.Y.Z-x64-setup.exe` or `.msi` on the GitHub Release. Local packaging existed (`build-windows-desktop.ps1 -Device`) but nothing harvested into WiX or uploaded.

**Fix:** `scripts/packaging/build-windows-msi.ps1` + WiX 5 `Files` harvest + Burn setup.exe; upload to `v0.7.2`; `windows-device-installers` job on `windows-latest` in `release.yml`. Pin WiX **5.0.2** (4.x lacks `Files`; 7+ requires OSMF EULA). Assets unsigned until HUMAN signing. OpenVEX gap unchanged (KB-015).

## KB-018 — Ship v0.7.2 gitleaks vault fixtures + CodeQL pin (2026-10-20)

**Symptom:** Security Scan (Gitleaks) failed on `tests/test_device/test_secrets_vault.py` (`generic-api-key` on high-entropy vault fixture strings). Separately, `update-deps --apply` again rewrote `github/codeql-action` to unresolvable `vcodeql-bundle-v2.27.2`. Do not paste sample key assignment literals into KB notes — gitleaks scans docs too.

**Fix:** Use low-entropy `fixture` strings in vault tests; restore `codeql-action@v4`; re-apply branch protection. Release Please #49 → `v0.7.2`; `uv lock` sync. OpenVEX still a known workflow gap (KB-015/016).

## KB-017 — Ship v0.7.1 Secret Sauce + CodeQL pin recurrence (2026-10-19)

**Symptom:** `/ship` after Secret Sauce Lab; `update-deps` again pinned `github/codeql-action@vcodeql-bundle-v2.27.2`; CI pytest `test_masks_for_rsx_cross_period` got `None` from live RSX; `/regress` `wait-release-sbom --require` fails without `openvex.json`; `verify-branch-protection` needs admin (H-003).

**Fix:** Restore `codeql-action@v4`; stub `_rsx_series` in the RSX mask unit test; Release Please #48 → `v0.7.1`; `uv lock` sync. CycloneDX SBOMs present on the release; OpenVEX still a known workflow gap (KB-015/016).

## KB-016 — Ship v0.7.0 CodeQL pin + TEMPLATE_INDEX + OpenVEX gap (2026-10-17)

**Symptom:** `/ship` CI red after `update-deps` pinned `github/codeql-action@vcodeql-bundle-v2.27.2` (unresolvable); overwriting child `TEMPLATE_INDEX.json` with full-template paths failed validate-template-index; `mcp.web.example` missing broke pytest; new `scripts/summarize-coverage.sh` was UNINDEXED.

**Fix:** Restore `codeql-action@v4` (and Scorecard SARIF upload); keep child `TEMPLATE_INDEX`; index coverage script; commit `.cursor/mcp.web.example`. After Release Please, `uv lock` → commit. `wait-release-sbom --require` still fails without `openvex.json` (CycloneDX assets present on v0.7.0) — same gap as KB-015 note. Branch-protection verify needs admin token (H-003).

## KB-015 — Linux CI hangs after green pytest summary (2026-10-16)

**Symptom:** `uv run pytest` prints coverage + `N passed in Xs`, then the GHA step never exits (~10m) until `timeout` (exit 124). Orphan PIDs labeled `pytest` appear at job cleanup.

**Fix:** `tests/conftest.py` calls `os._exit(status)` on `CI=true` in `pytest_unconfigure` (disable with `TRENDALGO_CI_FORCE_EXIT=0`). Also: pandas fallbacks for BBANDS/PLUS_DI/SAR without TA-Lib; CI `--cov-fail-under=55` when device/LTS suites are ignored; omit `*/device/*` from coverage; Release Please version bumps need `uv lock` sync.

**Note:** `wait-release-sbom --require` still expects `openvex.json`, but `release.yml` only uploads CycloneDX SBOMs — treat OpenVEX as a known gap until the workflow emits it.

## KB-014 — v0.5.0 ship (2026-07-12)

**Symptom:** `/ship` after product-rec + R-Audit-8; CI red on (1) `uv.lock` version drift after Release Please, (2) More menu always visible (`display:flex` overriding `[hidden]`), (3) e2e update tests using `page.route("**/*")` that bypassed API mocks.

**Fix:** After every Release Please merge run `uv lock` and commit; add `.gp-nav-more-menu[hidden]{display:none}`; narrow update mocks to `app-update.json` + GitHub releases only. Close Dependabot group bumps that include TypeScript majors. Pages deploy 404 until GitHub Pages is enabled (HUMAN). Local WSL1 breaks `feature-gate`/`check-license-compliance` — use CI + Windows `npx tsc` / `uv run pytest`.

## Template KB entries

Legacy template entries (KB-007+) remain in git history; TrendAlgo-specific entries start at KB-001 above.
