# Audit remediation (Phases 1–9)

Durable copy of the approved audit roadmap. BUILD_PLAN Sprint Audit-P1…P9 owns status.
Sequencing: phases **1→5 sequential**; 6–9 may interleave only after Phase 5 ✅.
ELv2 license swap approved by human 2026-11-11 (1A).

## Hard constraints

- Pull `origin/main` ff-only before writes; never overwrite Argus (`.agent/`, `argus*`, `rules.manifest.json`, Argus workflows/docs, README “What this is not”).
- Gates per commit: ruff, mypy --strict, pytest, semgrep, gitleaks.
- Test-first; dry-run default; `decide_live` sole live/paper truth; float money; no second live flag.

## Path corrections

| Claim | Fact |
|-------|------|
| `api/deps.py` | Create; auth today in `api/owner_auth.py` + `trading/signed_command.py` |
| TV webhook open | Partially wrong — HMAC already in `signals/tradingview.py`; AUTH-04 hardens |
| Prod compose | `docker/docker-compose.prod.yml` |
| Desktop decision | ADR-0016 Accepted — amend for Study UI |
| `ws.py` | Delete in PWA-03 (device uses `ws="none"`) |
| HOUSE-09 | Argus-safe: archive specs only; keep `.agent/` / argus |

## Phase map

| Phase | IDs | Prereqs |
|-------|-----|---------|
| 1 Security | AUTH-01…05 | — |
| 2 PWA | PWA-01…04 | Phase 1 |
| 3 License | LIC-01…02 | Phase 2; before public beta |
| 4 Risk | RISK-01…10 | Phase 3 |
| 5 Sim | SIM-01…11 | Phase 4; re-baseline Net % after SIM-01/02 |
| 6 Billing | BILL-01…08 | AUTH-01 + SIM-01/02; AUTH-01 before BILL-04 |
| 7 Live/Notif | LIVE-01…05, NOTIF-01…03 | SIM-05/06 |
| 8 Features | FEAT-01…06 | Phase 5 |
| 9 House | HOUSE-01…09 | Phase 5; HOUSE-09 Argus-safe |

## AUTH model

`require_owner` accepts HMAC signed command **or** short-lived bearer. Apply at router include.
Exempt (documented in `deps.py`): `GET /health`, `GET /version`, `POST /webhooks/tradingview`, plus intentional open GETs listed in the same table.
TV webhook: body-once dependency + existing HMAC + rate limit.
Prod bind: `127.0.0.1:8080:8080`; remote via SSH tunnel / Tailscale.
CORS default empty; credentials only with explicit origins.

## Acceptance (summary)

Each task ID has a failing test before the fix, then gates green. See BUILD_PLAN rows and original audit for full criteria.
