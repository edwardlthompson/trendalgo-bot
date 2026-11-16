"""Primary-filter → ETA coin projection and last-scan meta (pure; no Qt)."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from trendalgo.device.lts_scan_model import FILTERS_FILE, lane_data_file
from trendalgo.device.profile import mutate_json

META_ELAPSED = "last_scan_elapsed_s"
META_FINISHED = "last_scan_finished_at"
META_FUNNEL = "last_funnel"
_META_KEYS = (META_ELAPSED, META_FINISHED, META_FUNNEL)
_VOL_POWER = 0.4


def projected_scan_coins(
    funnel: dict[str, Any] | None,
    *,
    min_volume_usd: float,
    require_continuous_1h: bool = True,
    fallback_n: int = 1,
) -> int:
    """Estimate qualified coin count from last-scan funnel + current primary filters."""
    fb = max(1, int(fallback_n))
    if not isinstance(funnel, dict):
        return fb
    try:
        listed = max(0, int(funnel.get("listed_n") or 0))
        after_vol = max(0, int(funnel.get("after_volume_n") or 0))
        after_act = max(0, int(funnel.get("after_activity_n") or after_vol))
        qualified = max(0, int(funnel.get("qualified_n") or 0))
        last_vol = float(funnel.get("min_volume_usd") or 0.0)
    except (TypeError, ValueError):
        return fb
    if listed <= 0 and after_vol <= 0 and qualified <= 0:
        return fb
    listed = max(listed, after_vol, after_act, qualified, 1)
    after_vol = min(listed, max(after_vol, after_act, qualified))
    after_act = min(after_vol, max(after_act, qualified))
    qualified = min(after_act, qualified)

    after_vol_p = _scale_volume(after_vol, listed=listed, last_vol=last_vol, new_vol=min_volume_usd)
    after_act_p = _scale_volume(after_act, listed=listed, last_vol=last_vol, new_vol=min_volume_usd)
    after_act_p = min(after_vol_p, after_act_p)
    base = after_act_p if require_continuous_1h else after_vol_p
    return max(1, min(listed, base))


def merge_scan_meta(
    root: Path,
    *,
    elapsed_s: float | None = None,
    funnel: dict[str, Any] | None = None,
) -> None:
    """Patch only last-scan meta keys under lock (never clobber UI filter prefs)."""

    def _apply(saved: dict[str, Any]) -> None:
        if elapsed_s is not None:
            try:
                saved[META_ELAPSED] = round(float(elapsed_s), 3)
                saved[META_FINISHED] = datetime.now(UTC).isoformat()
            except (TypeError, ValueError):
                pass
        if isinstance(funnel, dict) and funnel:
            saved[META_FUNNEL] = {
                "listed_n": max(0, int(funnel.get("listed_n") or 0)),
                "after_volume_n": max(0, int(funnel.get("after_volume_n") or 0)),
                "after_activity_n": max(
                    0, int(funnel.get("after_activity_n") or funnel.get("after_volume_n") or 0)
                ),
                "qualified_n": max(0, int(funnel.get("qualified_n") or 0)),
                "min_volume_usd": float(funnel.get("min_volume_usd") or 0.0),
                "require_continuous_1h": bool(funnel.get("require_continuous_1h", True)),
            }

    mutate_json(root / FILTERS_FILE, _apply)


def write_filters_ui(root: Path, payload: dict[str, Any], *, lane: str = "crypto") -> None:
    """Write UI filter prefs under lock, preserving any meta keys already on disk."""

    def _apply(saved: dict[str, Any]) -> None:
        meta = {k: saved[k] for k in _META_KEYS if k in saved}
        saved.clear()
        saved.update(payload)
        for key, value in meta.items():
            if key not in saved:
                saved[key] = value

    mutate_json(root / lane_data_file(FILTERS_FILE, lane), _apply)


def load_scan_meta(root: Path, *, lane: str = "crypto") -> dict[str, Any]:
    from trendalgo.device.lts_scan_model import load_filters

    saved = load_filters(root, lane=lane)
    return {
        META_ELAPSED: saved.get(META_ELAPSED),
        META_FINISHED: saved.get(META_FINISHED),
        META_FUNNEL: saved.get(META_FUNNEL) if isinstance(saved.get(META_FUNNEL), dict) else None,
    }


def preserve_scan_meta(payload: dict[str, Any], prior: dict[str, Any]) -> dict[str, Any]:
    """Keep duration/funnel keys when UI rewrite of filters would otherwise drop them."""
    out = dict(payload)
    for key in _META_KEYS:
        if key not in out and key in prior:
            out[key] = prior[key]
    return out


def _scale_volume(n: int, *, listed: int, last_vol: float, new_vol: float) -> int:
    last_eff = max(float(last_vol), 1.0)
    new_eff = max(float(new_vol), 1.0)
    if abs(last_eff - new_eff) < 1e-9:
        return max(1, min(listed, n))
    scaled = round(n * (last_eff / new_eff) ** _VOL_POWER)
    return max(1, min(listed, scaled))
