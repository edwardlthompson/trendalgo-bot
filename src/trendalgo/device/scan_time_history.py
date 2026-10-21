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


@dataclass
class TimingSample:
    elapsed_s: float
    n_strategies: int
    n_timeframes: int
    had_subhour: bool
    bars_base: int = 0
    ts: float = 0.0


@dataclass
class ScanTimeHistory:
    samples: list[TimingSample] = field(default_factory=list)
    # Empirical means (updated on save).
    mean_load_1h_s: float = _DEFAULT_LOAD_1H_S
    mean_load_1m_s: float = _DEFAULT_LOAD_1M_S
    mean_per_strat_tf_s: float = _DEFAULT_PER_STRAT_TF_S


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
                )
            )
        except (TypeError, ValueError):
            continue
    hist = ScanTimeHistory(
        samples=samples[-_MAX_SAMPLES:],
        mean_load_1h_s=float(raw.get("mean_load_1h_s") or _DEFAULT_LOAD_1H_S),
        mean_load_1m_s=float(raw.get("mean_load_1m_s") or _DEFAULT_LOAD_1M_S),
        mean_per_strat_tf_s=float(raw.get("mean_per_strat_tf_s") or _DEFAULT_PER_STRAT_TF_S),
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


def estimate_label(
    hist: ScanTimeHistory,
    *,
    n_strategies: int,
    n_timeframes: int,
    had_subhour: bool,
    n_coins: int = 1,
) -> str:
    per = estimate_coin_seconds(
        hist,
        n_strategies=n_strategies,
        n_timeframes=n_timeframes,
        had_subhour=had_subhour,
    )
    total = per * max(1, n_coins)
    return (
        f"Est. ~{_fmt_s(per)} per coin · ~{_fmt_s(total)} for {max(1, n_coins)} coin"
        f"{'s' if n_coins != 1 else ''}"
    )


def _recompute(hist: ScanTimeHistory) -> ScanTimeHistory:
    if len(hist.samples) < 3:
        return hist
    load_1h: list[float] = []
    load_1m: list[float] = []
    per_combo: list[float] = []
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
    if load_1h:
        hist.mean_load_1h_s = sum(load_1h) / len(load_1h)
    if load_1m:
        hist.mean_load_1m_s = sum(load_1m) / len(load_1m)
    if per_combo:
        hist.mean_per_strat_tf_s = sum(per_combo) / len(per_combo)
    return hist


def _fmt_s(seconds: float) -> str:
    if seconds < 60:
        return f"{seconds:.0f}s"
    mins = seconds / 60.0
    if mins < 60:
        return f"{mins:.1f}m"
    return f"{mins / 60.0:.1f}h"
