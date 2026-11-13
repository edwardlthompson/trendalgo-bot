"""Per strategy×timeframe×pair EWMA timing ledger for precise scan ETA."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from trendalgo.device.profile import read_json, write_json

PREFS_FILE = "scan_unit_timing.json"
LAST_RUN_FILE = "scan_timing_last.json"
_MAX_KEYS = 500
_ALPHA = 0.25
_DEF_UNIT = 0.08
_DEF_LOAD = 2.0
_DEF_DEEPEN = 5.0
_DEF_SAUCE = 8.0


@dataclass
class EwmaStat:
    mean_s: float = 0.0
    n: int = 0


@dataclass
class UnitTimingLedger:
    by_strat_tf: dict[str, EwmaStat] = field(default_factory=dict)
    by_strategy: dict[str, EwmaStat] = field(default_factory=dict)
    by_timeframe: dict[str, EwmaStat] = field(default_factory=dict)
    by_pair: dict[str, EwmaStat] = field(default_factory=dict)
    load_s: float = _DEF_LOAD
    deepen_s: float = _DEF_DEEPEN
    sauce_s: float = _DEF_SAUCE
    global_unit_s: float = _DEF_UNIT
    dirty: bool = False


@dataclass(frozen=True)
class UnitSample:
    strategy: str
    timeframe: str
    pair: str
    elapsed_s: float
    phase: str = "catalog"


def ledger_path(root: Path) -> Path:
    return root / PREFS_FILE


def strat_tf_key(strategy: str, timeframe: str) -> str:
    return f"{str(strategy or '').strip()}@{str(timeframe or '').strip()}"


def load_ledger(root: Path) -> UnitTimingLedger:
    raw = read_json(ledger_path(root))
    if not isinstance(raw, dict):
        return UnitTimingLedger()
    return UnitTimingLedger(
        by_strat_tf=_load_map(raw.get("by_strat_tf")),
        by_strategy=_load_map(raw.get("by_strategy")),
        by_timeframe=_load_map(raw.get("by_timeframe")),
        by_pair=_load_map(raw.get("by_pair")),
        load_s=float(raw.get("load_s") or _DEF_LOAD),
        deepen_s=float(raw.get("deepen_s") or _DEF_DEEPEN),
        sauce_s=float(raw.get("sauce_s") or _DEF_SAUCE),
        global_unit_s=float(raw.get("global_unit_s") or _DEF_UNIT),
    )


def save_ledger(root: Path, ledger: UnitTimingLedger) -> None:
    _trim(ledger)
    write_json(
        ledger_path(root),
        {
            "by_strat_tf": {
                k: {"mean_s": round(v.mean_s, 4), "n": v.n} for k, v in ledger.by_strat_tf.items()
            },
            "by_strategy": {
                k: {"mean_s": round(v.mean_s, 4), "n": v.n} for k, v in ledger.by_strategy.items()
            },
            "by_timeframe": {
                k: {"mean_s": round(v.mean_s, 4), "n": v.n} for k, v in ledger.by_timeframe.items()
            },
            "by_pair": {
                k: {"mean_s": round(v.mean_s, 4), "n": v.n} for k, v in ledger.by_pair.items()
            },
            "load_s": ledger.load_s,
            "deepen_s": ledger.deepen_s,
            "sauce_s": ledger.sauce_s,
            "global_unit_s": ledger.global_unit_s,
        },
    )
    ledger.dirty = False


def flush_ledger(root: Path, ledger: UnitTimingLedger) -> None:
    if not ledger.dirty:
        return
    try:
        save_ledger(root, ledger)
    except OSError:
        return


def record_units(ledger: UnitTimingLedger, samples: list[UnitSample]) -> None:
    for s in samples:
        _record(ledger, s)
    ledger.dirty = True


def lookup_unit_s(
    ledger: UnitTimingLedger, strategy: str, timeframe: str, *, fallback: float | None = None
) -> float:
    for bucket, key in (
        (ledger.by_strat_tf, strat_tf_key(strategy, timeframe)),
        (ledger.by_strategy, strategy),
        (ledger.by_timeframe, timeframe),
    ):
        stat = bucket.get(key)
        if stat is not None and stat.n > 0 and stat.mean_s > 0:
            return float(stat.mean_s)
    return float(fallback if fallback is not None else ledger.global_unit_s)


def estimate_catalog_wall_s(
    ledger: UnitTimingLedger,
    units: list[tuple[str, str]],
    *,
    workers: int,
    fallback: float | None = None,
) -> float:
    if not units:
        return 0.0
    total = sum(lookup_unit_s(ledger, a, b, fallback=fallback) for a, b in units)
    return total / max(1, int(workers))


def estimate_coin_wall_s(
    ledger: UnitTimingLedger,
    *,
    strategies: list[str] | tuple[str, ...],
    timeframes: list[str] | tuple[str, ...],
    workers: int,
    include_deepen_sauce: bool = True,
    fallback: float | None = None,
) -> float:
    units = [(sid, tf) for tf in timeframes for sid in strategies]
    wall = ledger.load_s + estimate_catalog_wall_s(
        ledger, units, workers=workers, fallback=fallback
    )
    if include_deepen_sauce:
        wall += ledger.deepen_s + ledger.sauce_s
    return max(0.5, wall)


def top_slowest(samples: list[UnitSample], n: int = 5) -> list[UnitSample]:
    return sorted(samples, key=lambda s: s.elapsed_s, reverse=True)[: max(0, int(n))]


def write_last_run(root: Path, payload: dict[str, Any]) -> None:
    write_json(root / LAST_RUN_FILE, payload)


def _record(ledger: UnitTimingLedger, sample: UnitSample) -> None:
    elapsed = max(0.0, float(sample.elapsed_s))
    phase = str(sample.phase or "catalog")
    if phase == "load":
        ledger.load_s = _ewma(ledger.load_s, elapsed, 1)
        return
    if phase == "deepen":
        ledger.deepen_s = _ewma(ledger.deepen_s, elapsed, 1)
        return
    if phase == "sauce":
        ledger.sauce_s = _ewma(ledger.sauce_s, elapsed, 1)
        return
    sid, tf, pair = sample.strategy.strip(), sample.timeframe.strip(), sample.pair.strip()
    if sid and tf:
        _touch(ledger.by_strat_tf, strat_tf_key(sid, tf), elapsed)
    if sid:
        _touch(ledger.by_strategy, sid, elapsed)
    if tf:
        _touch(ledger.by_timeframe, tf, elapsed)
    if pair:
        _touch(ledger.by_pair, pair, elapsed)
    ledger.global_unit_s = _ewma(ledger.global_unit_s, elapsed, 1)


def _touch(bucket: dict[str, EwmaStat], key: str, elapsed: float) -> None:
    stat = bucket.get(key) or EwmaStat()
    stat.mean_s = _ewma(stat.mean_s, elapsed, stat.n)
    stat.n += 1
    bucket[key] = stat


def _ewma(prev: float, sample: float, n: int) -> float:
    if n <= 0 or prev <= 0:
        return float(sample)
    return (1.0 - _ALPHA) * float(prev) + _ALPHA * float(sample)


def _trim(ledger: UnitTimingLedger) -> None:
    for bucket in (ledger.by_strat_tf, ledger.by_strategy, ledger.by_timeframe, ledger.by_pair):
        if len(bucket) <= _MAX_KEYS:
            continue
        keep = sorted(bucket.items(), key=lambda kv: kv[1].n, reverse=True)[:_MAX_KEYS]
        bucket.clear()
        bucket.update(keep)


def _load_map(raw: object) -> dict[str, EwmaStat]:
    out: dict[str, EwmaStat] = {}
    if not isinstance(raw, dict):
        return out
    for key, val in raw.items():
        if isinstance(val, dict):
            try:
                out[str(key)] = EwmaStat(
                    mean_s=float(val.get("mean_s") or 0), n=int(val.get("n") or 0)
                )
            except (TypeError, ValueError):
                continue
    return out
