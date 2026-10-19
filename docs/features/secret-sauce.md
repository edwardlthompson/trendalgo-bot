# Feature: Secret Sauce Lab

> Per-coin causal Enter/Exit that earns its place on the Oracle → Sauce → peers spectrum.
> Checklist: 🔲 open · ✅ done · ❌ blocked.

## Acceptance criteria

- ✅ Lab mines after Oracle with fee-aware P&L (scan fees), not label-coverage alone
- ✅ Multi-axis regime detector budgets search families (soft weights; always skim)
- ✅ Results can unlock before Lab finishes; Secret Sauce upserts when ready
- ✅ Spectrum badge is independent — never force-sort Sauce to #2
- ✅ Study shows regime chips, Oracle gap, English formula, anti-cheat note
- ✅ README pitch + this lab notebook explain how Sauce is cooked

## Smoke scenario

1. _Given_ Device Backtest All-TA on a liquid pair with Oracle max
2. _When_ catalog TA finishes (and Lab may still be cooking)
3. _Then_ Results show peers; Secret Sauce appears or updates with Enter/Exit formula
4. _And_ Study opens with regime axes + Net % vs B&H vs Oracle

## How it works (pitch-level)

Most backtests dump indicators and shrug. Secret Sauce is the app’s research buddy:
read the tape (regime), budget the right idea families, score with real fees, emit
plain-English Enter/Exit. Oracle is the hindsight ceiling; we do not peek and we do
not fake the sort order.

Blind RSI mean-reversion is looking for keys under the streetlight. Uptrends want
dip-in-uptrend math; quiet ranges want mean-reversion; chop is skim-and-admit.

## Regime axes (never conflate)

| Axis | Question |
|------|----------|
| Structural | Trend vs range / chop? |
| Volatility | Calm vs stressed? |
| Direction | Up / down / flat? |

### Structural votes (P0)

| Pattern | Trend read |
|---------|------------|
| ADX + DI+/DI− | ADX≥25 in / ≤20 out (hysteresis); DI = direction |
| Kaufman Efficiency Ratio | ER≥0.30 trend |
| Choppiness Index | CHOP≤55 trend vote; ≥61.8 chop |
| 2-of-3 ensemble | ≥2 of ADX/ER/CHOP agree → trending |
| MA ribbon | SMA20/50/100 stack + SMA20 slope |

### Volatility (P0)

| Pattern | Read |
|---------|------|
| ATR percentile (~50 bars) | <25 low · >75 high |
| BB width percentile | squeeze / expansion |
| TTM-style squeeze | BB inside Keltner → squeeze flag |

### Direction (P0)

DI dominance, close vs SMA50 + rising SMA20, optional MACD hist confirm.

## Family budget matrix

| Regime home | Fat budget | Skim |
|-------------|------------|------|
| trending × up | dip_uptrend, momentum | osc_cross, mean_reversion |
| trending × down | osc_cross, mean_reversion | dip_uptrend ≤0.1, squeeze skim |
| ranging × low vol | mean_reversion, osc_cross | momentum |
| squeeze (not down) | squeeze_breakout + structural winner | — |
| choppy / high-vol range | skim (+ light osc_cross) | — |
| volume_ok × trending up | volume_impulse co-boost | — |

Soft budgets only — never exclusive hard-switch. Regime label uses majority of last ~48 bars.

## Cross events vs level-state

Catalog RSX/RSI use **edge** crosses (`rsi_xup_30` / `rsi_xdn_70`). Lab `osc_cross` family
mines the same semantics. Sticky level-state (`rsi_14 <= 45`) stays skim-only so Sauce
cannot crown a churning long on a down tape while peers print positive crosses.

## Pattern reverse-mine (primary skill)

**Objective:** maximize fee Net % toward the Oracle ceiling (provable P&L math).
**Floor:** clear absolute max catalog peer so Results **#2** is earned — never the
finish line. Soft ladder only prevents stranding under B&H when #2 is unreachable
mid-search.

Secret Sauce runs toward Oracle, then fee-selects:

Two Results rows (both tinted like baselines):

1. **Secret Sauce TA** — after catalog Pass 2, score catalog entry/exit fires vs Oracle
   trough/peak bars (±1); compose best entry indicator + best exit indicator; upsert
   live (deterministic — not an LLM)
2. **Secret Sauce Lab** — deep mine (overlaps catalog) + Oracle-first refine (~12s);
   near-catalog feature bank (CDL/Fib/MOM/…); fee-max toward Oracle; peer Net % is the
   #2 validation floor only

Interactive All-TA Pass 2 is **parallel**; partial ranked rows stream to the Backtest
table while the progress bar advances; Lab upserts at the end.

Peer Net % remains the **validation floor** for Results #2 — not the recipe source.

Anti-cheat: never “enter at oracle index”; only causal thresholds at those bars.

## Anti-cheat

- Causal features only (bars ≤ i)
- No Oracle neighbor-pivot cloning as entries (fit features at bars, not indexes)
- Validate re-sim Net % matches trial (±eps)
- Spectrum fail still shows the row with a note
- Peer pattern + inspire mutate; never ships an exact peer photocopy

## Container map

| Layer | Path |
|-------|------|
| Lab API | `src/trendalgo/backtest/secret_sauce_lab/` |
| Features / mine | `secret_sauce_features.py`, `secret_sauce_mine.py`, `secret_sauce_search.py` |
| Device wire | `pair_strategy_secret_sauce.py`, `pair_strategy_scan.py` |
| Study UI | `views/secret_sauce_study.py` |
| Tests | `tests/test_backtest/test_secret_sauce*.py` |

## Definition of Done

- Unit tests: cross edge-only; downtrend starves dip; reseed rejects clones; soft
  ladder; peer-class CDL seeds; oracle/peer pattern mine; period-RSX validate;
  valley spectrum
- Slow smokes: **BTC / ETH / SOL / AVAX** All-TA Sauce rank == 2 (Oracle #1),
  Net % > B&H, formula ≠ top peer clone (skip if cache missing that base)
- `watch-agent-gates --once --autofix --scope auto` green after AGENT steps
- Root README Secret Sauce section stays honest to shipped behavior

## Smoke commands

```bash
uv run python -m trendalgo.device --smoke-backtest ETH/USD
uv run pytest tests/test_backtest/test_secret_sauce_lab.py tests/test_device/test_secret_sauce_smoke.py -q
```

## Notes

- Pitch: [README.md](../../README.md) (Secret Sauce details block)
- Operator-local `GEN_SECRET_*`; `requires_backtest: true`
