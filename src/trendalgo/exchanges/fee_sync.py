"""Sync exchange fees from public documentation pages into the fee database."""

from __future__ import annotations

import json
import os
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from typing import Any

from trendalgo.exchanges.fee_fetcher import fetch_exchange_fees
from trendalgo.exchanges.fee_store import _SEED_PATH, FeeStore
from trendalgo.exchanges.registry import load_registry

_FEE_EPS = 1e-9
_DEFAULT_STALE_DAYS = 30


def load_seed_config() -> tuple[str, dict[str, dict[str, Any]]]:
    if not _SEED_PATH.is_file():
        return "retail_default", {}
    data = json.loads(_SEED_PATH.read_text(encoding="utf-8"))
    tier = str(data.get("tier", "retail_default"))
    exchanges = {str(k): v for k, v in (data.get("exchanges") or {}).items()}
    return tier, exchanges


def _parse_ts(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def fees_differ(a: float, b: float) -> bool:
    return abs(a - b) > _FEE_EPS


def ensure_fee_db_ready(store: FeeStore, *, on_log: Callable[[str], None] | None = None) -> None:
    if store.count() == 0:
        count = store.seed_from_json()
        on_log and on_log(f"exchange fees: seeded {count} venues from config/exchange_fees.json")


def sync_exchange_fees(
    store: FeeStore,
    *,
    on_log: Callable[[str], None] | None = None,
) -> dict[str, Any]:
    registry = load_registry()
    tier, seeds = load_seed_config()
    updated: list[str] = []
    unchanged: list[str] = []
    fallback: list[str] = []
    failed: list[dict[str, str]] = []

    for entry in registry.exchanges:
        seed = seeds.get(entry.id)
        if seed is None:
            continue
        prev = store.get(entry.id)
        try:
            live = fetch_exchange_fees(entry.id, seed)
        except Exception as exc:
            prev_taker = float(prev["taker_pct"]) if prev else float(seed["taker_pct"])
            prev_maker = float(prev["maker_pct"]) if prev else float(seed["maker_pct"])
            if prev is None:
                store.upsert(
                    entry.id,
                    ccxt_id=entry.ccxt_id,
                    taker_pct=float(seed["taker_pct"]),
                    maker_pct=float(seed["maker_pct"]),
                    tier=tier,
                    source="documented",
                    source_url=str(seed.get("source_url", "")),
                )
            store.record_check(
                entry.id,
                "fetch_fallback",
                prev_taker=prev_taker,
                prev_maker=prev_maker,
                new_taker=float(seed["taker_pct"]),
                new_maker=float(seed["maker_pct"]),
                detail=str(exc),
            )
            fallback.append(entry.id)
            on_log and on_log(
                f"exchange fees: fetch blocked {entry.id} — using documented seed ({exc})"
            )
            continue

        prev_taker = float(prev["taker_pct"]) if prev else None
        prev_maker = float(prev["maker_pct"]) if prev else None
        changed = (
            prev is None
            or fees_differ(prev_taker, live.taker_pct)
            or fees_differ(prev_maker, live.maker_pct)
        )

        if live.source == "documented" and not live.verified:
            store.record_check(
                entry.id,
                "parse_fallback",
                prev_taker=prev_taker,
                prev_maker=prev_maker,
                new_taker=live.taker_pct,
                new_maker=live.maker_pct,
                detail=f"page fetched; using documented seed ({live.source_url})",
            )
            fallback.append(entry.id)
            on_log and on_log(
                f"exchange fees: fallback {entry.id} documented seed "
                f"taker={live.taker_pct} maker={live.maker_pct}"
            )
            store.upsert(
                entry.id,
                ccxt_id=entry.ccxt_id,
                taker_pct=float(prev["taker_pct"]) if prev else float(seed["taker_pct"]),
                maker_pct=float(prev["maker_pct"]) if prev else float(seed["maker_pct"]),
                tier=str(prev["tier"]) if prev else tier,
                source="documented",
                source_url=str(seed.get("source_url", "")),
            )
            continue

        if changed:
            # Never overwrite good documented fees with unverified parse drift.
            if live.source == "documented" and not live.verified:
                continue
            store.upsert(
                entry.id,
                ccxt_id=entry.ccxt_id,
                taker_pct=live.taker_pct,
                maker_pct=live.maker_pct,
                tier=str(prev["tier"]) if prev else tier,
                source=live.source,
                source_url=live.source_url,
            )
            store.record_check(
                entry.id,
                "updated",
                prev_taker=prev_taker,
                prev_maker=prev_maker,
                new_taker=live.taker_pct,
                new_maker=live.maker_pct,
                detail=f"public fee page ({live.source})",
            )
            updated.append(entry.id)
            on_log and on_log(
                f"exchange fees: UPDATED {entry.id} taker {prev_taker}->{live.taker_pct} "
                f"maker {prev_maker}->{live.maker_pct} ({live.source})"
            )
        else:
            if prev is not None and live.source in ("website", "website_verified"):
                store.upsert(
                    entry.id,
                    ccxt_id=entry.ccxt_id,
                    taker_pct=live.taker_pct,
                    maker_pct=live.maker_pct,
                    tier=str(prev["tier"]) if prev else tier,
                    source=live.source,
                    source_url=live.source_url,
                )
            store.record_check(
                entry.id,
                "unchanged",
                prev_taker=prev_taker,
                prev_maker=prev_maker,
                new_taker=live.taker_pct,
                new_maker=live.maker_pct,
                detail=live.source,
            )
            unchanged.append(entry.id)

    from trendalgo.exchanges import fees as fees_mod

    fees_mod.clear_fee_cache()

    summary = {
        "checked": len(updated) + len(unchanged) + len(fallback) + len(failed),
        "updated": updated,
        "unchanged": unchanged,
        "fallback": fallback,
        "failed": failed,
        "last_check": store.last_global_check(),
    }
    on_log and on_log(
        f"exchange fees sync: {len(updated)} updated, {len(unchanged)} unchanged, "
        f"{len(fallback)} fallback, {len(failed)} failed"
    )
    return summary


def is_stale(last_check: str | None, *, days: int = _DEFAULT_STALE_DAYS) -> bool:
    if not last_check:
        return True
    ts = _parse_ts(last_check)
    if ts is None:
        return True
    return datetime.now(UTC) - ts > timedelta(days=days)


def needs_initial_website_pull(store: FeeStore) -> bool:
    rows = store.list_all()
    live_sources = {"website", "website_verified", "documented"}
    return not rows or all(str(r.get("source")) not in live_sources for r in rows)


def startup_fee_sync(
    store: FeeStore,
    *,
    on_log: Callable[[str], None] | None = None,
) -> dict[str, Any] | None:
    if os.environ.get("TRENDALGO_FEE_SYNC_ON_START", "1").strip().lower() in ("0", "false", "no"):
        ensure_fee_db_ready(store, on_log=on_log)
        return None
    ensure_fee_db_ready(store, on_log=on_log)
    if needs_initial_website_pull(store) or is_stale(store.last_global_check()):
        on_log and on_log("exchange fees: syncing from public fee pages")
        return sync_exchange_fees(store, on_log=on_log)
    return None
