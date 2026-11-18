"""Scanner / Backtest Settings popup prefs (TFs, strategy denylist, signal set)."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import date
from pathlib import Path

from trendalgo.backtest.heartbeat_tf import (
    ALL_SCAN_TIMEFRAMES,
    HEARTBEAT_TIMEFRAMES,
    SUBHOUR_TIMEFRAMES,
    comparable_scan_timeframes,
    needs_1m_base,
    normalize_timeframes,
)
from trendalgo.backtest.ta_fleet import all_strategies
from trendalgo.device.opportunity_sauce import OPPORTUNITY_SAUCE_TOP_N
from trendalgo.device.profile import read_json, write_json
from trendalgo.device.scanner_signal_sets import BT_SET_ALL_TA, normalize_bt_signal_set
from trendalgo.market.kraken_ohlcvt import archive_ready
from trendalgo.market.kraken_ohlcvt_download import discover_joined_archive
from trendalgo.market.kraken_ohlcvt_meta import mix_allowed, read_archive_coverage
from trendalgo.market.ohlcvt_tip_journal import read_started as read_journal_started

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
    ohlcvt_path: str = ""
    ohlcvt_auto_tip: bool = True
    ohlcvt_journal_started: str = ""


def prefs_path(root: Path) -> Path:
    return root / PREFS_FILE


def default_prefs() -> ScanBtPrefs:
    return ScanBtPrefs()


def resolve_ohlcvt_path(root: Path, configured: str = "") -> str:
    """Use configured path when valid; else auto-detect Price Data ZIP."""
    raw = str(configured or "").strip()
    if archive_ready(raw):
        return raw
    found = discover_joined_archive(root)
    return str(found) if found is not None else raw


def deep_1m_ready(prefs: ScanBtPrefs | None = None, *, root: Path | None = None) -> bool:
    if prefs is None and root is not None:
        prefs = load_scan_bt_prefs(root)
    if prefs is None:
        return False
    path = prefs.ohlcvt_path
    if root is not None:
        path = resolve_ohlcvt_path(root, path)
    return archive_ready(path)


def bands_mix_ready(prefs: ScanBtPrefs | None = None, *, root: Path | None = None) -> bool:
    """True when sub-hour and 1h–24h may be selected together."""
    if prefs is None and root is not None:
        prefs = load_scan_bt_prefs(root)
    if prefs is None:
        return False
    path = prefs.ohlcvt_path
    if root is not None:
        path = resolve_ohlcvt_path(root, path)
    cov = read_archive_coverage(path) if archive_ready(path) else None
    started = journal_started_date(prefs, root=root)
    return mix_allowed(cov, journal_started=started)


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
        legacy = read_json(root / "scanner_filters.json")
        prefs = default_prefs()
        if isinstance(legacy, dict) and "bt_signal_set" in legacy:
            prefs.bt_signal_set = normalize_bt_signal_set(legacy.get("bt_signal_set"))
        prefs.ohlcvt_path = resolve_ohlcvt_path(root, "")
        return prefs
    ohlcvt = resolve_ohlcvt_path(root, str(raw.get("ohlcvt_path") or "").strip())
    tip_raw = raw.get("ohlcvt_auto_tip")
    started = _normalize_started(
        raw.get("ohlcvt_journal_started"), fallback=read_journal_started(root)
    )
    mix = mix_allowed(
        read_archive_coverage(ohlcvt) if archive_ready(ohlcvt) else None,
        journal_started=_parse_started(started),
    )
    tfs = list(comparable_scan_timeframes(normalize_timeframes(raw.get("timeframes")), deep_1m=mix))
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
        ohlcvt_path=ohlcvt,
        ohlcvt_auto_tip=True if tip_raw is None else bool(tip_raw),
        ohlcvt_journal_started=started,
    )


def journal_started_date(prefs: ScanBtPrefs | None, *, root: Path | None = None) -> date | None:
    if prefs is not None and prefs.ohlcvt_journal_started:
        try:
            return date.fromisoformat(prefs.ohlcvt_journal_started[:10])
        except ValueError:
            pass
    if root is not None:
        return read_journal_started(root)
    return None


def _normalize_started(raw: object, *, fallback: date | None) -> str:
    text = str(raw or "").strip()
    if text:
        try:
            return date.fromisoformat(text[:10]).isoformat()
        except ValueError:
            pass
    return fallback.isoformat() if fallback is not None else ""


def save_scan_bt_prefs(root: Path, prefs: ScanBtPrefs) -> None:
    started = _normalize_started(prefs.ohlcvt_journal_started, fallback=read_journal_started(root))
    path = str(prefs.ohlcvt_path or "").strip()
    mix = mix_allowed(
        read_archive_coverage(path) if archive_ready(path) else None,
        journal_started=_parse_started(started),
    )
    clean = ScanBtPrefs(
        timeframes=list(comparable_scan_timeframes(prefs.timeframes, deep_1m=mix)),
        strategy_denylist=[str(x).strip() for x in prefs.strategy_denylist if str(x).strip()],
        bt_signal_set=normalize_bt_signal_set(prefs.bt_signal_set),
        sauce_with_scan=bool(prefs.sauce_with_scan),
        sauce_top_n=clamp_sauce_top_n(prefs.sauce_top_n),
        market_context_with_scan=bool(prefs.market_context_with_scan),
        ohlcvt_path=path,
        ohlcvt_auto_tip=bool(prefs.ohlcvt_auto_tip),
        ohlcvt_journal_started=started,
    )
    if not clean.timeframes:
        clean.timeframes = list(HEARTBEAT_TIMEFRAMES)
    write_json(prefs_path(root), asdict(clean))


def selected_timeframes(prefs: ScanBtPrefs, *, root: Path | None = None) -> tuple[str, ...]:
    tfs = comparable_scan_timeframes(prefs.timeframes, deep_1m=bands_mix_ready(prefs, root=root))
    return tfs if tfs else HEARTBEAT_TIMEFRAMES


def _parse_started(raw: str) -> date | None:
    text = str(raw or "").strip()
    if not text:
        return None
    try:
        return date.fromisoformat(text[:10])
    except ValueError:
        return None


def enabled_strategies(denylist: list[str] | None = None) -> tuple[str, ...]:
    blocked = {str(x).strip() for x in (denylist or []) if str(x).strip()}
    return tuple(name for name in all_strategies() if name not in blocked)


def prefs_need_1m(prefs: ScanBtPrefs) -> bool:
    return needs_1m_base(selected_timeframes(prefs))


def catalog_timeframes() -> tuple[str, ...]:
    return ALL_SCAN_TIMEFRAMES


def catalog_subhour() -> tuple[str, ...]:
    return SUBHOUR_TIMEFRAMES
