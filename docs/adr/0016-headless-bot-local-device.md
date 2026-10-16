# ADR-0016 — Headless bot host with a local device app

- **Status:** Accepted (2026-10-09; owner approved the plan, and the live host was decided the same day)
- **Date:** 2026-10-09
- **Relates to:** ADR-0002 (hosting; decision 5 superseded), ADR-0005 and ADR-0008 (monetization), ADR-0012 (hosted URL), ADR-0013 (LTS vendor), ADR-0014 and ADR-0015 (desktop path; amended), ADR-0017 (tenant boundary and license terms)
- **Plan:** `local_device_headless_bot` (approved 2026-10-09). Risk items cited here are in [docs/RISK_REGISTER.md](../RISK_REGISTER.md), section "Local device and headless bot register".

## Context

- The owner wants heavy work on this PC: LTS scans, backtests, plan building, the journal, and a guided setup wizard. Only the approved plan and its execution should run on an always-on host that the owner controls.
- The PWA and the pywebview shell are retired in favor of a native PySide6 (Qt) app.
- Verified in the code on 2026-10-09 (citations in the register):
  - The bot runs through `BotOrchestrator` and `scheduler.py` in the current codebase. A fresh database gets an enabled "Bot-1" (H1).
  - Live approval is spread across several flags and routes (H2).
  - Live orders are sized with a price of 1.0, so the base amount equals the USD amount (E1).
  - The risk and license gate returns before exits run (R5).
  - Live bots run native strategies. The LTS engine that was backtested does not run live (L9).

## Decision

1. **Two components.**
   - **Device** (this PC): PySide6 app with Scanner, Backtests, Plan builder, Bot status and Journal, Settings, and the setup wizard. The device never holds exchange keys.
   - **Host** (a VPS the owner controls): new headless package `src/trendalgo/botd/`. It runs the approved plan 24/7, holds exchange keys in its own encrypted SecretStore, and has no UI.
2. **Device-initiated sync only.** The device sends `PUT /api/v1/plan` and `POST /api/v1/commands`, and pulls `GET /api/v1/events` and `GET /api/v1/status`. Nothing calls back into the PC, so the PC needs no inbound port. Each request carries an HMAC over method, path, timestamp, nonce, body, and `owner_id`. The device pins the host's TLS certificate fingerprint.
3. **The host runs the LTS engine.** A streaming port of the LTS trade loop (`src/trendalgo/lts_vendor/backtesting/engine.py`) and its indicators (`signals.py`, `SIGNAL_REGISTRY`) runs on the host, so live trading executes what was backtested. Native strategies stay backtest-only in v1.
4. **Exit policy.** Exits are the bot's trade signals plus an optional per-bot trailing stop. Entry guards (risk, exchange, entitlements) block new entries only. Exits, stops, and flatten are never gated (R5). There are no exchange-side stop orders in v1 (accepted risk R-STOP).
5. **Sizing policy.** Each bot is sized at creation: a fixed USD amount per entry, or a percentage of equity. Backtests use the same sizing. A live base size is the USD amount divided by a fresh ticker price, with market precision and minimum-size checks (E1).
6. **One live gate.** The host's `LiveGate` is the only path that can enable live orders (H2). These existing paths stop enabling live on the host: `GO_LIVE_APPROVED` and `WORLDWIDE_TRADING_ACK` (`src/trendalgo/trading/multi_exchange.py`), `TV_EXECUTION_ACK` (`src/trendalgo/signals/runner_bridge.py`), the `go_live_approved` flags in `src/trendalgo/trading/control.py` and `src/trendalgo/dex/control.py`, `validate_pre_live` in `src/trendalgo/risk/protections.py`, and the venue approval in `src/trendalgo/api/routes/platform.py`. `scripts/go-live-gate.sh` is re-pointed at the signed command and keeps its audit trail.
7. **Shadow first.** The host starts in shadow mode (no real orders). At least 14 days of shadow, with a clean divergence report, come before any live order (P5).
8. **Hosting.** Path A: Oracle Always Free A1, sized at 2 OCPU and 12 GB in total (the Always Free allowance). Path B: a paid VPS on amd64 or arm64. Oracle's Always Free page says idle A1 instances may be reclaimed. It does not say that a Pay As You Go upgrade prevents this. Owner decision (2026-10-09): live runs on Path A (Oracle A1), and the owner accepts the reclamation risk. Shadow may run on either path.
9. **Retire the PWA and the pywebview shell** in P7, after the device app and wizard pass their exit tests. Until then the PWA stays runnable.

## Supersedes and amends

These take effect on acceptance, 2026-10-09.

- **ADR-0002, decision 5 (co-location) is superseded.** The bot, API, web UI, and SQLite no longer share one instance. Decisions 1 to 4 still hold: production on an external always-on VPS, Oracle preferred, Hetzner as fallback, and Render for dev only.
- **ADR-0014 is amended.** The primary operator path becomes the PySide6 device app. The browser launcher and one-origin serving with `TRENDALGO_SERVE_WEB=1` retire with the PWA (P7).
- **ADR-0015 is amended and superseded for the device UI.** The pywebview shell is replaced by the PySide6 app and retired in P7.
- **ADR-0012 needs its own follow-up.** Its hosted dry-run URL depends on the PWA, so it must be amended or superseded when P7 lands.

## Consequences

- New packages: `src/trendalgo/botd/` (host) and `src/trendalgo/device/` (app). `docker/Dockerfile.bot` builds for linux/amd64 and linux/arm64.
- P1 safety work (E1 to E8, R1 to R5, H1 to H3, H6) must pass before any live path is enabled.
- The desktop app's forced `TRENDALGO_MODE=dry-run` (`src/trendalgo/desktop/app.py`) is removed with the desktop shell (P7).
- Live orders need a host that cannot be reclaimed, H-032 sign-off, and a flatten drill (P6).
- PySide6 is LGPL-3.0. Qt stays dynamically linked, and notices ship with the app (`foss-compliance.mdc`).
- Wizard copy must match the verified Oracle facts: the home region is fixed when the account is created, budget alerts are evaluated every 24 hours, and an upgrade charges only for usage above the Always Free limits.

## Alternatives considered

- **Keep the bot in the API process on a VPS (ADR-0002 as written).** Rejected. The UI and the runtime stay coupled, and live runs native strategies, not the backtested engine.
- **Run the bot on the PC.** Rejected. The PC sleeps, restarts, and can lose power or network. That is the reliability problem ADR-0002 was written to avoid.
- **Exchange-side stop orders in v1.** Deferred. They can be added later as a per-bot option.
- **Caddy for TLS.** Not used. Uvicorn terminates TLS with a self-signed certificate that the device pins.
- **Third-party scripts that retry Oracle capacity.** Rejected. They hold cloud credentials.
- **TradingView webhook or Telegram ingress as trade input.** Off by default. Each adds inbound attack surface.

## Open items

- **Live host.** Decided 2026-10-09: Path A (Oracle A1) for live, accepting the reclamation risk. The compounded risk with R-STOP is recorded in register item W-OCI1.
- **H-004 hosting eligibility.** `scripts/check-hosting-eligibility.sh` is a stub. It only checks that `docs/DEPLOYMENT.md` exists. The eligibility check is manual.
- **Stop data.** REST polling of the forming candle (v1), or a direct Kraken trade feed. Owner decision.
- **H-032 live sign-off.** Human only.

## Acceptance

Accepted on 2026-10-09, because these held:

- `AGENT.md` was rewritten on the owner's instruction (G1), and BUILD_PLAN rows tagged `[LOCAL]` or `[CLOUD]` with `— scope:` were added (sprint S-Headless-1).
- The live host (Path A, risk accepted) and stop data (REST polling, the plan default) are recorded.
- ADR-0017 is reviewed alongside this ADR.
