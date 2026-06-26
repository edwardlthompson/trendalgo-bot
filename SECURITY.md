# Security Policy

## Supported Versions

Supported template version: see `.template-version` on `main`. Security fixes apply to the latest Release Please tag.

| Version | Supported          |
| ------- | ------------------ |
| latest  | :white_check_mark: |
| < latest| :x:                |

## Threat Model

See [`docs/THREAT_MODEL.md`](docs/THREAT_MODEL.md) and [`docs/PRIVACY.md`](docs/PRIVACY.md) for data-boundary expectations.

## Reporting a Vulnerability

**Do not** open public GitHub issues for security vulnerabilities.

1. Use GitHub **Private vulnerability reporting** (Security → Advisories → Report a vulnerability), or
2. Email the maintainers listed in `CODEOWNERS` with:
   - Description of the vulnerability
   - Steps to reproduce
   - Impact assessment
   - Suggested fix (if any)

## Response Timeline

| Stage | Target |
|-------|--------|
| Acknowledgment | 3 business days |
| Initial assessment | 7 business days |
| Fix or mitigation plan | 30 days (severity-dependent) |
| Public disclosure | Coordinated with reporter |

## Security Practices

- Dependabot alerts and weekly CVE triage: see [`docs/SECURITY_TRIAGE.md`](docs/SECURITY_TRIAGE.md)
- Maintainer orchestrator: `bash scripts/run-maintainer-gates.sh` (weekly; full cycle omits `--quick`)
- Secrets must never be committed (Gitleaks pre-commit enforced)
- Report dependency vulnerabilities via Dependabot; do not commit patched forks without review

## Security Onboarding (TrendAlgo — M11 / S10)

1. Create Kraken API keys with **trade only** — never enable Withdraw permission
2. Store keys in `.env` only; run `bash scripts/setup-secrets.sh` (H-008/H-011)
3. Enable 2FA on exchange and VPS provider
4. Review `docs/THREAT_MODEL.md` before live trading
5. Run `bash scripts/check-api-key-policy.sh` before Sprint 10 release

See `docs/features/security-onboarding.md` for full wizard (Sprint 10).
