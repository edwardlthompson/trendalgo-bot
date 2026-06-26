# Prompt Library — TrendAlgo Bot

> Reusable Cursor prompts. Expand at milestone boundaries.

## 1. Sprint kickoff

```
Read @BUILD_PLAN.md Sprint N Sequential lane.
Run python3 scripts/founder_gate.py preflight-sprint --sprint N.
Execute [AGENT] tasks in order; after each step run watch-agent-gates --once --autofix.
```

## 2. Feature vertical slice (Sprint 2+)

```
Implement docs/features/{name}.md per docs/FEATURE_MODULES.md.
Logic in src/trendalgo/{domain}/, view in examples/web/src/{feature}/.
Run watch-agent-gates after wiring.
```

## 3. Legal compliance check

```
Before any billing or payment UX: read docs/LEGAL_SAFETY.md and ADR-0008.
Run bash scripts/check-legal-compliance.sh — must PASS.
```

## 4. Go-live preparation

```
Run go-live-gate.sh --check-only.
Confirm external VPS deploy per docs/DEPLOYMENT.md.
HUMAN approve H-010 before enabling live config.
```

## 5. Risk Register Zero

```
bash scripts/check-risk-mitigations.sh --strict --sprint N
Document closures in docs/RISK_REGISTER_CLOSED.md
```

_Template prompts 6–9 from bootstrap remain available in git history for reference._
