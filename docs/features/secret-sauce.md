# Feature: Secret Sauce (helpers → Final Boss)

> Per-coin causal Enter/Exit helpers feeding a fee-honest Final Boss on the Oracle → Sauce → peers spectrum.
> Checklist: 🔲 open · ✅ done · ❌ blocked.
> Spec: [`docs/specs/secret-sauce-oracle-gap.md`](../specs/secret-sauce-oracle-gap.md)

## Acceptance criteria

- ✅ Lab mines after Oracle with fee-aware P&L (scan fees), not label-coverage alone
- ✅ Multi-axis regime detector budgets search families (soft weights; always skim)
- ✅ Results unlock before Lab finishes; Secret Sauce upserts when ready
- ✅ Spectrum badge independent — never force-sort Sauce to #2
- ✅ Study shows regime chips, Oracle gap, English formula, anti-cheat note
- ✅ Phase 0–2: residual indexes, residual AND, adaptive_exit, soft holdout ladder
- ✅ **No Sauce wall-clock caps** (`lab_time_budget_s` → +inf); progress per helper
- ✅ Helpers: Peer (A), Armed (B), Exit (C) as first-class Results rows
- ✅ Final Boss (E/O): ≥2 agree ±1 or best-holdout; Study lists voters; create-bot prefers Final
- ✅ S5: dual-horizon, regime peers, CCI/WILLR/MFI residual bank, session mask, scale-out proxy
- ✅ S6: teacher / genetic / MFE / vol targeting / veto / meta-TSL feed Final (silent or meta)
- ❌ Out of scope: **M** BTC veto · **R** cross-coin transfer

## Smoke scenario

1. _Given_ Device Backtest All-TA on a liquid pair with Oracle max
2. _When_ catalog TA finishes (helpers may still cook)
3. _Then_ Results show peers + Sauce TA / Lab / Peer / Armed / Exit / Final when fee-valid
4. _And_ Study on Final lists voters; create-bot defaults to Final when present

## How it works (pitch-level)

Specialists each own one skill. **Secret Sauce Final** combines their causal signals
with a fee re-sim — not a Net % average. Oracle is the hindsight ceiling; we do not
peek indexes and we do not fake the sort order.

## Container map

| Layer | Path |
|-------|------|
| Lab + helpers | `src/trendalgo/backtest/secret_sauce_lab/` (`sauce_cook.py`, `final_boss.py`, `helper_*.py`) |
| Names | `src/trendalgo/device/sauce_names.py` |
| Device wire | `pair_strategy_secret_sauce.py`, `pair_strategy_scan.py` |
| Study UI | `views/secret_sauce_study.py` |
| Tests | `tests/test_backtest/test_secret_sauce_helpers_final.py`, `tests/test_device/test_sauce_names.py` |
## Definition of Done

- Unit tests: names preference; session mask; scale-out proxy; Final vote path; uncapped budget
- Slow smokes: BTC/ETH All-TA still honest (Lab/Final may land under peer with spectrum note)
- `watch-agent-gates --once --autofix --scope auto` green after AGENT steps

## Smoke commands

```bash
uv run pytest tests/test_backtest/test_secret_sauce_helpers_final.py \
  tests/test_device/test_sauce_names.py -q
python scripts/agent-run.py watch-agent-gates --once --autofix --scope auto

```
