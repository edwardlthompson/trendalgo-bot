"""Portfolio sync + trading status load tests (CM-6, S17/S20)."""

from __future__ import annotations

import os
import tempfile
import uuid
from pathlib import Path

from trendalgo.exchanges.registry import list_trading_exchanges, load_registry
from trendalgo.exchanges.sync import sync_all_exchanges
from trendalgo.portfolio.db import PortfolioStore
from trendalgo.trading.multi_exchange import list_supported_exchanges

MIN_EXCHANGES = 9
MIN_TRADING_VENUES = 9
MIN_WORLDWIDE_PHASE = 2
MAX_ELAPSED_SEC = 30.0
WORLDWIDE_TRADING_IDS = frozenset({"binance", "bybit", "okx"})


def run_load_test(
    *, min_exchanges: int = MIN_EXCHANGES, max_sec: float = MAX_ELAPSED_SEC
) -> dict[str, object]:
    os.environ.setdefault("TRENDALGO_SYNC_STAGGER_SEC", "0")
    tmp = Path(tempfile.gettempdir()) / f"trendalgo-load-{uuid.uuid4().hex}"
    tmp.mkdir(parents=True, exist_ok=True)
    db_path = tmp / "portfolio.db"
    store = PortfolioStore(db_path)
    try:
        result = sync_all_exchanges(store, dry_run=True)
    finally:
        del store
        try:
            db_path.unlink(missing_ok=True)
            tmp.rmdir()
        except OSError:
            pass
    elapsed = float(result.get("elapsed_sec", 999))
    count = int(result.get("exchange_count", 0))
    ok = count >= min_exchanges and elapsed < max_sec
    return {
        "ok": ok,
        "exchange_count": count,
        "elapsed_sec": elapsed,
        "max_sec": max_sec,
        "min_exchanges": min_exchanges,
        "registry_version": result.get("registry_version"),
    }


def run_trading_status_check(
    *,
    min_trading_venues: int = MIN_TRADING_VENUES,
    min_worldwide_phase: int = MIN_WORLDWIDE_PHASE,
) -> dict[str, object]:
    """Registry + router parity for N-exchange trading (no HTTP server required)."""
    registry = load_registry()
    trading = list_supported_exchanges()
    worldwide = {entry.id for entry in list_trading_exchanges() if entry.us_restricted}
    trading_set = set(trading)
    ok = (
        registry.version >= 6
        and registry.worldwide_trading_phase >= min_worldwide_phase
        and len(trading) >= min_trading_venues
        and WORLDWIDE_TRADING_IDS.issubset(trading_set)
        and worldwide == WORLDWIDE_TRADING_IDS
    )
    return {
        "ok": ok,
        "registry_version": registry.version,
        "worldwide_trading_phase": registry.worldwide_trading_phase,
        "trading_exchange_count": len(trading),
        "min_trading_venues": min_trading_venues,
        "worldwide_exchanges": sorted(worldwide),
        "trading_exchanges": trading,
    }


def run_n_exchange_ops_validation(
    *, min_exchanges: int = MIN_EXCHANGES, max_sec: float = MAX_ELAPSED_SEC
) -> dict[str, object]:
    """S20 CM-6: 9+ venue portfolio sync and trading status gates."""
    portfolio = run_load_test(min_exchanges=min_exchanges, max_sec=max_sec)
    trading = run_trading_status_check(min_trading_venues=min_exchanges)
    ok = bool(portfolio["ok"] and trading["ok"])
    return {
        "ok": ok,
        "portfolio_sync": portfolio,
        "trading_status": trading,
    }
