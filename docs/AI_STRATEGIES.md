# AI-Recommended Strategies

> **ADR-0009:** No community marketplace or user-uploaded strategies. Value = LTS Scanner + operator-curated AI recommendations.

## Recommender logic (AI5)

The recommender scores registered templates using:

| Input | Effect |
|-------|--------|
| Active LTS scanner opportunities | Boosts `scanner` and `strong-uptrend-scanner` templates |
| Low drawdown / circuit breaker | Boosts defensive templates (DCA, multi-TF) |
| Small account equity | Boosts DCA |
| Balanced profile | Boosts grid and multi-TF |

Every suggestion includes `requires_backtest: true` and `user_confirms_params: true`.

## Scanner-to-strategy pipeline (AI6)

Qualified pairs from the latest scanner snapshot map to:

- High uniformity + gain → `strong-uptrend-scanner` with tuned `lts_uniform_min`
- High volatility gain → `grid-trading`
- Otherwise → `smart-dca`

## Curated library (AI7)

Versioned presets in `src/trendalgo/ai/curated_library.py` — operator-maintained JSON only. No user uploads.

## Natural-language draft (AI8)

- **Production default:** rule-based parser (`nl_draft.py`)
- **Dev optional:** Ollama when `OLLAMA_HOST` is set
- User must confirm all parameters before deploy

## Growth (G1, G2)

- Referral codes: pseudonymous hash of install UUID (no email/PII)
- Leaderboard: opt-in only; pseudonym `trader-{hash}`; score = net worth snapshot at opt-in

## Boost Mode (B1)

Optional 15% performance license rate (vs 12% standard) for premium curated AI documentation. User-initiated enrollment via API.

## Legal disclaimers

- Software tool only — **not financial advice**
- User responsible for all trades and parameter confirmation
- Backtest before live; dry-run is default until go-live gate
- No auto-withdraw or custodial collection (ADR-0008)

## Rejected (CI enforced)

- Community strategy marketplace (G3)
- Community indicator import (IX1)
- User-uploaded strategy imports (CM1, IX2)
- Hosted multi-tenant trading keys (ADR-0008)

Verification: `bash scripts/check-legal-compliance.sh`
