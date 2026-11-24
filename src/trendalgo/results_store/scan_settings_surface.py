"""Scan/BT settings surface — TF + strategy checklist over scan_bt_prefs.json."""

from __future__ import annotations

from dataclasses import asdict, replace
from pathlib import Path
from typing import Any

from trendalgo.backtest.heartbeat_tf import (
    HEARTBEAT_TIMEFRAMES,
    SUBHOUR_TIMEFRAMES,
    comparable_scan_timeframes,
)
from trendalgo.backtest.ta_fleet import all_strategies
from trendalgo.device.scan_bt_prefs import (
    bands_mix_ready,
    catalog_timeframes,
    enabled_strategies,
    journal_started_date,
    load_scan_bt_prefs,
    resolve_ohlcvt_path,
    save_scan_bt_prefs,
    selected_timeframes,
)
from trendalgo.market.kraken_ohlcvt import archive_ready
from trendalgo.market.kraken_ohlcvt_copy import format_subhour_mix_note
from trendalgo.market.kraken_ohlcvt_meta import read_archive_coverage
from trendalgo.results_store.scan_settings_eta import scan_settings_eta
from trendalgo.results_store.scan_settings_lanes import apply_lane_settings, lane_settings_view


def _tf_band_payload(prefs: Any, *, root: Path) -> dict[str, Any]:
    mix = bands_mix_ready(prefs, root=root)
    path = resolve_ohlcvt_path(root, prefs.ohlcvt_path)
    cov = read_archive_coverage(path) if archive_ready(path) else None
    note = format_subhour_mix_note(cov, journal_started=journal_started_date(prefs, root=root))
    return {
        "bands_mix_ready": mix,
        "subhour_mix_note": note,
        "tf_bands": [
            {
                "id": "subhour",
                "title": "Sub-hour",
                "timeframes": list(SUBHOUR_TIMEFRAMES),
            },
            {
                "id": "hours",
                "title": "Hours (1h–24h) · live 30-day window",
                "timeframes": list(HEARTBEAT_TIMEFRAMES),
            },
        ],
    }


def scan_settings_view(root: Path) -> dict[str, Any]:
    prefs = load_scan_bt_prefs(root)
    selected = set(selected_timeframes(prefs, root=root))
    deny = {str(x).strip() for x in prefs.strategy_denylist if str(x).strip()}
    body = {k: v for k, v in asdict(prefs).items() if k not in ("timeframes", "strategy_denylist")}
    return {
        **body,
        **_tf_band_payload(prefs, root=root),
        **lane_settings_view(root),
        "eta": scan_settings_eta(root, prefs),
        "timeframes": [{"id": tf, "enabled": tf in selected} for tf in catalog_timeframes()],
        "strategies": [{"id": name, "enabled": name not in deny} for name in all_strategies()],
        "enabled_strategy_count": len(enabled_strategies(prefs.strategy_denylist)),
        "enabled_tf_count": len(selected),
    }


def _ids_enabled(rows: object) -> list[str]:
    if not isinstance(rows, list):
        return []
    out: list[str] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        ident = str(row.get("id") or "").strip()
        if not ident:
            continue
        if bool(row.get("enabled")):
            out.append(ident)
    return out


def apply_scan_settings(root: Path, payload: dict[str, Any]) -> dict[str, Any]:
    """Merge checklist payload into scan_bt_prefs; refuse empty TF or empty strategies."""
    prefs = load_scan_bt_prefs(root)
    tfs = _ids_enabled(payload.get("timeframes"))
    if not tfs:
        return {"ok": False, "error": "empty_timeframes", "prefs": scan_settings_view(root)}
    enabled = _ids_enabled(payload.get("strategies"))
    if not enabled:
        return {"ok": False, "error": "empty_strategies", "prefs": scan_settings_view(root)}
    mix = bands_mix_ready(prefs, root=root)
    tfs = list(comparable_scan_timeframes(tfs, deep_1m=mix))
    if not tfs:
        return {"ok": False, "error": "empty_timeframes", "prefs": scan_settings_view(root)}
    catalog = set(all_strategies())
    denylist = sorted(catalog - set(enabled))
    sauce_n = payload.get("sauce_top_n", prefs.sauce_top_n)
    ohlcvt_raw = payload.get("ohlcvt_path", prefs.ohlcvt_path)
    ohlcvt_path = resolve_ohlcvt_path(root, str(ohlcvt_raw or "").strip())
    tip_raw = payload.get("ohlcvt_auto_tip", prefs.ohlcvt_auto_tip)
    updated = replace(
        prefs,
        timeframes=tfs,
        strategy_denylist=denylist,
        sauce_with_scan=bool(payload.get("sauce_with_scan", prefs.sauce_with_scan)),
        market_context_with_scan=bool(
            payload.get("market_context_with_scan", prefs.market_context_with_scan)
        ),
        sauce_top_n=int(sauce_n) if sauce_n is not None else prefs.sauce_top_n,
        ohlcvt_path=ohlcvt_path,
        ohlcvt_auto_tip=bool(tip_raw),
    )
    # Re-evaluate exclusivity after path change (deep_1m may unlock).
    mix_after = bands_mix_ready(updated, root=root)
    updated = replace(
        updated,
        timeframes=list(comparable_scan_timeframes(tfs, deep_1m=mix_after)),
    )
    save_scan_bt_prefs(root, updated)
    apply_lane_settings(root, payload)
    return {"ok": True, "prefs": scan_settings_view(root)}
