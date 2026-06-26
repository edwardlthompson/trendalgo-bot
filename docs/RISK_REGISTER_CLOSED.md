# Risk Register — Closed

> Append-only archive. Active register: [`RISK_REGISTER.md`](RISK_REGISTER.md). Catalog: [`risk-catalog.json`](risk-catalog.json).

| R-ID | Title | Status | Sprint | Note | Closed at |
|------|-------|--------|--------|------|-----------|
| R-006 | Auto-withdraw / MSB | eliminated | S0 | ADR-0008 CI grep | 2026-06-25T23:39:29+00:00 |
| R-015 | SQLite insufficient at scale | closed | S12 | Postgres migration path + dual-write adapter | 2026-06-25 |

## Sprint 12 bulk closure

All remaining catalog risks moved to terminal status (`closed`, `ongoing`, `accepted`, or `eliminated`) on Sprint 12 sign-off. See `docs/risk-catalog.json` for per-risk `closed_at` timestamps.

## Critiques closed

| C-ID | Critique | Closed sprint | R-IDs |
|------|----------|---------------|-------|
| C-014 | SQLite will not scale | 12 | R-015 |
| C-001 | Cannot auto-collect from Kraken | 0 | R-006 |
| C-002 | Users will not pay | 10 | R-007 |
| C-003 | Open source no revenue | 11 | R-012 |
| C-004 | API keys nightmare | 10 | R-009 |
| C-005 | Legally gray license | 10 | R-008 |
| C-006 | Fee calculation wrong | 10 | R-005, R-031 |
| C-007 | Too complex for solo dev | 0 | R-018 |
| C-008 | Scanner merge breaks LTS | 4 | R-013 |
| C-009 | Fork removes billing | 11 | R-012 |
| C-010 | Community strategies dangerous | 0 | R-006 |
| C-011 | AI equals financial advice | 11 | R-023 |
| C-012 | Drawdown fees unfair | 10 | R-011 |
| C-013 | Auto-collect only monetization | 0 | R-006 |
| C-015 | No light mode or mobile UX | 5 | R-022 |
| C-016 | No legal protection | 10 | R-019, R-008 |
| C-017 | CoinStats looks better | 5 | R-017, R-022 |
| C-018 | Performance license equals adviser | 10 | R-008 |
| C-019 | 38 features never shipping | 0 | R-018 |
| C-020 | Webhook signals hijack bot | 4 | R-037 |
| C-021 | Single VPS single point of failure | 4 | R-038 |
