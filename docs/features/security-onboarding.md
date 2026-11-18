# Feature: Security onboarding (exchange API keys)

> First-run / Settings guidance for exchange keys. Checklist: ✅ done where shipped.
> Trigger: Coinigy-class third-party key revoke advisories (2026-11-13).

## Acceptance criteria

- ✅ Docs state **trade + query only** — never Withdraw / Transfer
- ✅ Docs recommend **IP allowlists** when the venue supports them
- ✅ Docs forbid **reusing** bot keys with third-party portfolio/trading SaaS
- ✅ Device Settings key help echoes the same rules (`SETTINGS_KEYS_HELP`)
- ✅ Breach response steps live in [`SECURITY_TRIAGE.md`](../SECURITY_TRIAGE.md)

## Operator happy path

1. Create exchange API keys with **trade + query** (or query-only for portfolio sync).
2. Disable withdraw/transfer; enable IP allowlist to the VPS if available.
3. Paste keys only into the device vault / VPS `.env` — never into chat or third-party dashboards.
4. Keep `TRENDALGO_MODE=dry-run` until `go-live-gate.sh --approve` per exchange.

## Offline / error

- Missing keys: public Kraken research desk still works; portfolio/keyed scan stay empty with honest empty states.
- Third-party breach: revoke keys shared with that vendor; rotate TrendAlgo keys; see Security Triage.

## Definition of Done

- Canonical limits: [`API_ACCESS_LIMITS.md`](../API_ACCESS_LIMITS.md)
- Threat notes: [`THREAT_MODEL.md`](../THREAT_MODEL.md) (key compromise)
- Triage: [`SECURITY_TRIAGE.md`](../SECURITY_TRIAGE.md) § Exchange API-key hygiene
- Device copy: `SETTINGS_KEYS_HELP` / scope help in `src/trendalgo/device/strings.py`

## Smoke

```bash
# Docs present and cross-linked (no runtime gate).
test -f docs/features/security-onboarding.md
rg -n "no withdraw|IP allowlist|not reused|Coinigy" docs/API_ACCESS_LIMITS.md docs/SECURITY_TRIAGE.md docs/features/security-onboarding.md

```
