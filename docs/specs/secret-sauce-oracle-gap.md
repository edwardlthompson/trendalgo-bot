# Spec: Secret Sauce — close Oracle gap

> Status: Phase 0–1 shipped. Phases 2–4 are follow-on only.
> Feature notebook: [`docs/features/secret-sauce.md`](../features/secret-sauce.md)

## Locked decisions

- Do **not** wire the full TA catalog into the Lab feature bank or search.
- Residual-driven selective features only; keep sparsity and fee honesty.
- Spectrum never force-sorts Sauce to #2. Anti-cheat rules stay intact.

## Shipped (Phase 0–1)

| Phase | What |
|-------|------|
| **0** | `residual_entry_indexes` / `residual_exit_indexes` / `residual_feature_hits` / `oracle_gap_net_pct` on `HeartbeatDossier`; Study residual line |
| **1a** | `residual_mine.try_residual_refine` — AND one causal conjunct on missed Oracle bars; fee re-sim; OR deferred (CompositeRule is AND-only) |
| **1b** | `adaptive_exit` family seeds + exit-preferential search pass (champion entry × diverse exits) |

## Follow-on (Phase 2–4)

| Phase | Work | Depends on |
|-------|------|------------|
| **2** | Holdout-aware soft ladder inside `search_best_pair` (~65% train / holdout gate). Lagged higher-TF regime **arming** on primary TF (extend `multi_tf_lab.py` beyond keep-best). Recompute coverage on every refine. | Phase 0 metrics |
| **3** | ±2–3 bar neighborhood relative features. Add **CCI, WILLR, MFI** (cross/level binaries) only where residual_feature_hits show demand; optional `adx_strong` / SuperTrend–SAR exit state. | Residual histograms from live runs |
| **4** | Sparse two-recipe ensemble + optional Ultimate Sauce spectrum row (never force-sort). | Stable Phase 1–3 |

## Non-goals

- Bulk-adding catalog indicators to Lab search
- Force-sorting Sauce to #2 / cloning peer formulas / Oracle indexes
- Changing the scan fee schedule

## Validation

```bash
uv run pytest tests/test_backtest/test_secret_sauce_lab.py \
  tests/test_backtest/test_residual_instrument.py \
  tests/test_backtest/test_residual_mine.py \
  tests/test_backtest/test_adaptive_exit_family.py \
  tests/test_device/test_secret_sauce_smoke.py -q
python scripts/agent-run.py watch-agent-gates --once --autofix --scope auto
```
