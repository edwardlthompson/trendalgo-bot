"""Scanner / Backtest Settings popup prefs (TFs, strategy denylist, signal set)."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path

from trendalgo.backtest.heartbeat_tf import (
    ALL_SCAN_TIMEFRAMES,
    HEARTBEAT_TIMEFRAMES,
    SUBHOUR_TIMEFRAMES,
    needs_1m_base,
    normalize_timeframes,
    sort_timeframes,
)
from trendalgo.backtest.ta_fleet import all_strategies
from trendalgo.device.opportunity_sauce import OPPORTUNITY_SAUCE_TOP_N
from trendalgo.device.profile import read_json, write_json
from trendalgo.device.scanner_signal_sets import BT_SET_ALL_TA, normalize_bt_signal_set

PREFS_FILE = "scan_bt_prefs.json"
SAUCE_TOP_N_MIN = 1
SAUCE_TOP_N_MAX = 50


@dataclass
class ScanBtPrefs:
    timeframes: list[str] = field(default_factory=lambda: list(HEARTBEAT_TIMEFRAMES))
    strategy_denylist: list[str] = field(default_factory=list)
    bt_signal_set: str = BT_SET_ALL_TA
    sauce_with_scan: bool = True
    sauce_top_n: int = OPPORTUNITY_SAUCE_TOP_N
    market_context_with_scan: bool = True


def prefs_path(root: Path) -> Path:
    return root / PREFS_FILE


def default_prefs() -> ScanBtPrefs:
    return ScanBtPrefs()


def clamp_sauce_top_n(raw: object) -> int:
    try:
        n = int(raw)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        n = OPPORTUNITY_SAUCE_TOP_N
    return max(SAUCE_TOP_N_MIN, min(SAUCE_TOP_N_MAX, n))


def load_scan_bt_prefs(root: Path) -> ScanBtPrefs:
    path = prefs_path(root)
    raw = read_json(path)
    if not isinstance(raw, dict):
        # One-time migrate signal set from legacy scanner_filters.json.
        legacy = read_json(root / "scanner_filters.json")
        prefs = default_prefs()
        if isinstance(legacy, dict) and "bt_signal_set" in legacy:
            prefs.bt_signal_set = normalize_bt_signal_set(legacy.get("bt_signal_set"))
        return prefs
    tfs = normalize_timeframes(raw.get("timeframes"))
    if not tfs:
        tfs = list(HEARTBEAT_TIMEFRAMES)
    deny = raw.get("strategy_denylist")
    denylist = [str(x).strip() for x in deny if str(x).strip()] if isinstance(deny, list) else []
    sauce_with = raw.get("sauce_with_scan")
    mc_with = raw.get("market_context_with_scan")
    return ScanBtPrefs(
        timeframes=tfs,
        strategy_denylist=denylist,
        bt_signal_set=normalize_bt_signal_set(raw.get("bt_signal_set")),
        sauce_with_scan=True if sauce_with is None else bool(sauce_with),
        sauce_top_n=clamp_sauce_top_n(raw.get("sauce_top_n", OPPORTUNITY_SAUCE_TOP_N)),
        market_context_with_scan=True if mc_with is None else bool(mc_with),
    )


def save_scan_bt_prefs(root: Path, prefs: ScanBtPrefs) -> None:
    clean = ScanBtPrefs(
        timeframes=list(sort_timeframes(normalize_timeframes(prefs.timeframes))),
        strategy_denylist=[str(x).strip() for x in prefs.strategy_denylist if str(x).strip()],
        bt_signal_set=normalize_bt_signal_set(prefs.bt_signal_set),
        sauce_with_scan=bool(prefs.sauce_with_scan),
        sauce_top_n=clamp_sauce_top_n(prefs.sauce_top_n),
        market_context_with_scan=bool(prefs.market_context_with_scan),
    )
    write_json(prefs_path(root), asdict(clean))


def selected_timeframes(prefs: ScanBtPrefs) -> tuple[str, ...]:
    tfs = normalize_timeframes(prefs.timeframes)
    return sort_timeframes(tfs) if tfs else HEARTBEAT_TIMEFRAMES


def enabled_strategies(denylist: list[str] | None = None) -> tuple[str, ...]:
    blocked = {str(x).strip() for x in (denylist or []) if str(x).strip()}
    return tuple(name for name in all_strategies() if name not in blocked)


def prefs_need_1m(prefs: ScanBtPrefs) -> bool:
    return needs_1m_base(selected_timeframes(prefs))


def catalog_timeframes() -> tuple[str, ...]:
    return ALL_SCAN_TIMEFRAMES


def catalog_subhour() -> tuple[str, ...]:
    return SUBHOUR_TIMEFRAMES
