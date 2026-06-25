# Risk Register — TrendAlgo Bot

| Risk | Level | Mitigation |
|------|-------|------------|
| Accidental live trading | High | Dry-run default; H-010/H-028 |
| Regulatory (performance license) | High | H-006/H-023 attorney; ADR-0008 |
| Auto-withdraw / MSB | Critical | **Rejected** — user-initiated only |
| Key compromise | High | User VPS; trade+query only; SECURITY.md |
| CoinStats parity miss | Medium | H-015/H-017; P19/P20 S5 |
| AGPL fork without billing | Medium | AI recommender value AI5–AI8 |
| Community untrusted code | — | **Eliminated** — ADR-0009 no community imports |
| AI bad recommendations | Medium | User confirms params; backtest-first; AI_STRATEGIES.md |
| Scope creep / burnout | High | Phased sprints; S5 before S10 |
| Solo dev — 154 items | High | Sprint gates; CANONICAL_PLAN phased |

Full registry: `docs/CANONICAL_PLAN.md` § Risks & Critiques.
