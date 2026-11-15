"""Rolling scan/backtest timing history for live ETA estimates."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path

from trendalgo.device.profile import read_json, write_json

PREFS_FILE = "scan_time_history.json"
_MAX_SAMPLES = 40
# Conservative seeds until enough samples exist (seconds).
_DEFAULT_LOAD_1H_S = 2.0
_DEFAULT_LOAD_1M_S = 45.0
_DEFAULT_PER_STRAT_TF_S = 0.08
# Market Context compute after candles (~0.5–1.5s); Sauce Lab is serial and heavy.
_DEFAULT_MC_S = 0.9
_DEFAULT_SAUCE_S = 45.0


@dataclass
class TimingSample:
    elapsed_s: float
    n_strategies: int
    n_timeframes: int
    had_subhour: bool
    bars_base: int = 0
    ts: float = 0.0
    mc_s: float = 0.0
    sauce_s: float = 0.0


@dataclass
class ScanTimeHistory:
    samples: list[TimingSample] = field(default_factory=list)
    # Empirical means (updated on save).
    mean_load_1h_s: float = _DEFAULT_LOAD_1H_S
    mean_load_1m_s: float = _DEFAULT_LOAD_1M_S
    mean_per_strat_tf_s: float = _DEFAULT_PER_STRAT_TF_S
    mean_mc_s: float = _DEFAULT_MC_S
    mean_sauce_s: float = _DEFAULT_SAUCE_S


def history_path(root: Path) -> Path:
    return root / PREFS_FILE


def load_history(root: Path) -> ScanTimeHistory:
    raw = read_json(history_path(root))
    if not isinstance(raw, dict):
        return ScanTimeHistory()
    samples: list[TimingSample] = []
    for item in raw.get("samples") or []:
        if not isinstance(item, dict):
            continue
        try:
            samples.append(
                TimingSample(
                    elapsed_s=float(item.get("elapsed_s") or 0),
                    n_strategies=max(0, int(item.get("n_strategies") or 0)),
                    n_timeframes=max(0, int(item.get("n_timeframes") or 0)),
                    had_subhour=bool(item.get("had_subhour")),
                    bars_base=max(0, int(item.get("bars_base") or 0)),
                    ts=float(item.get("ts") or 0),
                    mc_s=max(0.0, float(item.get("mc_s") or 0)),
                    sauce_s=max(0.0, float(item.get("sauce_s") or 0)),
                )
            )
        except (TypeError, ValueError):
            continue
    hist = ScanTimeHistory(
        samples=samples[-_MAX_SAMPLES:],
        mean_load_1h_s=float(raw.get("mean_load_1h_s") or _DEFAULT_LOAD_1H_S),
        mean_load_1m_s=float(raw.get("mean_load_1m_s") or _DEFAULT_LOAD_1M_S),
        mean_per_strat_tf_s=float(raw.get("mean_per_strat_tf_s") or _DEFAULT_PER_STRAT_TF_S),
        mean_mc_s=float(raw.get("mean_mc_s") or _DEFAULT_MC_S),
        mean_sauce_s=float(raw.get("mean_sauce_s") or _DEFAULT_SAUCE_S),
    )
    return _recompute(hist)


def save_history(root: Path, hist: ScanTimeHistory) -> None:
    hist = _recompute(hist)
    write_json(
        history_path(root),
        {
            "samples": [asdict(s) for s in hist.samples[-_MAX_SAMPLES:]],
            "mean_load_1h_s": hist.mean_load_1h_s,
            "mean_load_1m_s": hist.mean_load_1m_s,
            "mean_per_strat_tf_s": hist.mean_per_strat_tf_s,
            "mean_mc_s": hist.mean_mc_s,
            "mean_sauce_s": hist.mean_sauce_s,
        },
    )


def record_sample(root: Path, sample: TimingSample) -> ScanTimeHistory:
    hist = load_history(root)
    hist.samples.append(sample)
    hist.samples = hist.samples[-_MAX_SAMPLES:]
    save_history(root, hist)
    return hist


def estimate_coin_seconds(
    hist: ScanTimeHistory,
    *,
    n_strategies: int,
    n_timeframes: int,
    had_subhour: bool,
) -> float:
    load = hist.mean_load_1m_s if had_subhour else hist.mean_load_1h_s
    work = max(0, n_strategies) * max(0, n_timeframes) * hist.mean_per_strat_tf_s
    return max(0.5, load + work)


def estimate_scan_seconds(
    hist: ScanTimeHistory,
    *,
    n_strategies: int,
    n_timeframes: int,
    had_subhour: bool,
    n_coins: int = 1,
    market_context: bool = True,
    sauce_with_scan: bool = False,
    sauce_top_n: int = 0,
) -> tuple[float, float, float, float]:
    """Return ``(catalog_total, mc_total, sauce_total, grand_total)`` seconds."""
    coins = max(1, int(n_coins))
    per = estimate_coin_seconds(
        hist,
        n_strategies=n_strategies,
        n_timeframes=n_timeframes,
        had_subhour=had_subhour,
    )
    catalog = per * coins
    mc = (max(0.0, float(hist.mean_mc_s)) * coins) if market_context else 0.0
    sauce_n = max(0, min(int(sauce_top_n), coins)) if sauce_with_scan else 0
    sauce = max(0.0, float(hist.mean_sauce_s)) * sauce_n
    return catalog, mc, sauce, catalog + mc + sauce


def estimate_label(
    hist: ScanTimeHistory,
    *,
    n_strategies: int,
    n_timeframes: int,
    had_subhour: bool,
    n_coins: int = 1,
    market_context: bool = True,
    sauce_with_scan: bool = False,
    sauce_top_n: int = 0,
) -> str:
    catalog, mc, sauce, total = estimate_scan_seconds(
        hist,
        n_strategies=n_strategies,
        n_timeframes=n_timeframes,
        had_subhour=had_subhour,
        n_coins=n_coins,
        market_context=market_context,
        sauce_with_scan=sauce_with_scan,
        sauce_top_n=sauce_top_n,
    )
    coins = max(1, int(n_coins))
    per = catalog / coins
    parts = [
        f"Est. ~{_fmt_s(per)} catalog/coin · ~{_fmt_s(total)} total for {coins} coin"
        f"{'s' if coins != 1 else ''}"
    ]
    if market_context:
        parts.append(f"MC ~{_fmt_s(mc)} (~{_fmt_s(hist.mean_mc_s)}/coin)")
    else:
        parts.append("MC off")
    if sauce_with_scan and sauce_top_n > 0:
        parts.append(
            f"Sauce ~{_fmt_s(sauce)} "
            f"(top {min(int(sauce_top_n), coins)} × ~{_fmt_s(hist.mean_sauce_s)})"
        )
    else:
        parts.append("Sauce off")
    return " · ".join(parts)


def _recompute(hist: ScanTimeHistory) -> ScanTimeHistory:
    if len(hist.samples) < 3:
        return hist
    load_1h: list[float] = []
    load_1m: list[float] = []
    per_combo: list[float] = []
    mc_vals: list[float] = []
    sauce_vals: list[float] = []
    for s in hist.samples:
        combos = max(1, s.n_strategies * max(1, s.n_timeframes))
        # Attribute ~30% of elapsed to load when subhour, else ~15%.
        load_frac = 0.35 if s.had_subhour else 0.15
        load_s = s.elapsed_s * load_frac
        work_s = max(0.0, s.elapsed_s - load_s)
        if s.had_subhour:
            load_1m.append(load_s)
        else:
            load_1h.append(load_s)
        per_combo.append(work_s / combos)
        if s.mc_s > 0:
            mc_vals.append(s.mc_s)
        if s.sauce_s > 0:
            sauce_vals.append(s.sauce_s)
    if load_1h:
        hist.mean_load_1h_s = sum(load_1h) / len(load_1h)
    if load_1m:
        hist.mean_load_1m_s = sum(load_1m) / len(load_1m)
    if per_combo:
        hist.mean_per_strat_tf_s = sum(per_combo) / len(per_combo)
    if mc_vals:
        hist.mean_mc_s = sum(mc_vals) / len(mc_vals)
    if sauce_vals:
        hist.mean_sauce_s = sum(sauce_vals) / len(sauce_vals)
    return hist


def _fmt_s(seconds: float) -> str:
    if seconds < 60:
        return f"{seconds:.0f}s"
    mins = seconds / 60.0
    if mins < 60:
        return f"{mins:.1f}m"
    return f"{mins / 60.0:.1f}h"
