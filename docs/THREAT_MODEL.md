# Threat Model — TrendAlgo Bot

> Sprint 0 draft. Update when FastAPI + live trading ships (Sprint 3–4).

## Scope

| Item | Value |
|------|-------|
| Project | TrendAlgo Bot |
| Stack | Python (native CCXT runner + FastAPI) + Web PWA |
| Methodology | STRIDE + OWASP ASVS (web) |

## Trust Boundaries

```text
[User browser/PWA] --> [FastAPI on VPS] --> [SQLite / Postgres]
                              |
                    [Native CCXT runner] --> [CEX APIs (CCXT)]
                              |
                    [Telegram API] (outbound alerts only)
```

**Production boundary:** External VPS only — never PR local LAN for live trading.

## STRIDE Summary

| Threat | Example | Mitigation |
|--------|---------|------------|
| Spoofing | Fake webhook to bot | HMAC + allowlist (R-037, S4 T4) |
| Tampering | Modified strategy file | Git + signed releases |
| Repudiation | Disputed license fee | Append-only fee ledger + export |
| Information disclosure | API keys in logs | Redaction; no Withdraw keys |
| Denial of service | Webhook flood | Rate limits |
| Elevation | Live trade without gate | go-live-gate.sh (R-003) |

## Top Abuse Cases

1. **Key compromise** — trade-only keys; encryption at rest M11 (R-009)
2. **Accidental live trading** — dry-run default; go-live gate
3. **Webhook hijack** — TradingView HMAC (S4)
4. **Fee gaming** — bot-attributed trades only; wash heuristics (S10)
5. **AI hallucination as advice** — disclaimers + user confirmation (R-021, R-023)

## Review Cadence

- `[HUMAN]` Milestone boundaries
- `[AUTO]` Weekly security triage + `check-risk-mitigations.sh --ongoing`
