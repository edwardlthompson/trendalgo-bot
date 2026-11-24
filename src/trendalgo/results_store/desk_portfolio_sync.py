"""Live keyed-only multi-exchange portfolio sync for Avalonia Dashboard."""

from __future__ import annotations

import json
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from trendalgo.device.alpaca_vault import resolve_alpaca_credentials
from trendalgo.device.secrets_vault import VaultSecretStore
from trendalgo.exchanges.asset_mapper import normalize_asset
from trendalgo.exchanges.base import holdings_from_ccxt_balance
from trendalgo.exchanges.private_client import ccxt_client, set_secret_store
from trendalgo.exchanges.registry import ExchangeEntry, list_portfolio_exchanges
from trendalgo.portfolio.db import HoldingRow, PortfolioStore
from trendalgo.portfolio.multi_exchange import aggregate_holdings

__all__ = ["EXTRAS_FILE", "run_live_portfolio_sync"]

EXTRAS_FILE = "portfolio_live_extras.json"


def _local_date_str() -> str:
    return datetime.now().astimezone().date().isoformat()


def _utc_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


def _resolve_ticker_map(
    exchange: Any,
    balance: dict[str, Any],
    usd_aliases: frozenset[str],
    quote: str,
) -> tuple[dict[str, Any], dict[str, float]]:
    try:
        raw = exchange.fetch_tickers()
        tickers: dict[str, Any] = dict(raw) if isinstance(raw, dict) else {}
    except Exception:
        tickers = {}

    changes: dict[str, float] = {}
    all_usd = frozenset({*usd_aliases, "USD", "ZUSD", "USDT", "USDC"})
    for raw_asset, qty in (balance.get("total") or {}).items():
        try:
            if float(qty or 0) <= 0:
                continue
        except (TypeError, ValueError):
            continue
        sym = normalize_asset(str(raw_asset))
        if sym in all_usd or sym.startswith("USD"):
            changes[sym] = 0.0
            continue
        matched: dict[str, Any] | None = None
        for q in (quote, "USD", "USDT", "USDC"):
            t = tickers.get(f"{sym}/{q}")
            if isinstance(t, dict) and t.get("last") is not None:
                matched = t
                break
        if matched is None:
            for q in (quote, "USD", "USDT", "USDC"):
                pair = f"{sym}/{q}"
                try:
                    t = exchange.fetch_ticker(pair)
                except Exception:
                    continue
                if isinstance(t, dict) and t.get("last") is not None:
                    tickers[pair] = t
                    matched = t
                    break
        if matched is not None and matched.get("percentage") is not None:
            try:
                changes[sym] = round(float(matched["percentage"]), 2)
            except (TypeError, ValueError):
                pass
    return tickers, changes


def _fetch_cex_extras(
    exchange: Any,
    venue: str,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], float]:
    open_orders: list[dict[str, Any]] = []
    recent_trades: list[dict[str, Any]] = []
    fees_usd = 0.0
    try:
        raw_orders = exchange.fetch_open_orders()
        if isinstance(raw_orders, list):
            for o in raw_orders[:25]:
                if not isinstance(o, dict):
                    continue
                open_orders.append(
                    {
                        "venue": venue,
                        "pair": str(o.get("symbol") or ""),
                        "side": str(o.get("side") or ""),
                        "type": str(o.get("type") or ""),
                        "price": float(o.get("price") or 0.0),
                        "amount": float(o.get("amount") or 0.0),
                        "timestamp": str(o.get("datetime") or o.get("timestamp") or ""),
                    }
                )
    except Exception:
        pass
    try:
        raw_trades = exchange.fetch_my_trades(limit=25)
        if isinstance(raw_trades, list):
            for tr in raw_trades[:25]:
                if not isinstance(tr, dict):
                    continue
                fee_obj = tr.get("fee")
                fee_cost = 0.0
                if isinstance(fee_obj, dict) and fee_obj.get("cost") is not None:
                    try:
                        fee_cost = float(fee_obj["cost"])
                    except (TypeError, ValueError):
                        fee_cost = 0.0
                fees_usd += fee_cost
                recent_trades.append(
                    {
                        "venue": venue,
                        "pair": str(tr.get("symbol") or ""),
                        "side": str(tr.get("side") or ""),
                        "price": float(tr.get("price") or 0.0),
                        "amount": float(tr.get("amount") or 0.0),
                        "cost_usd": float(tr.get("cost") or 0.0),
                        "fee_usd": round(fee_cost, 4),
                        "timestamp": str(tr.get("datetime") or tr.get("timestamp") or ""),
                    }
                )
    except Exception:
        pass
    return open_orders, recent_trades, round(fees_usd, 4)


def _sync_single_cex(
    entry: ExchangeEntry,
    vault: VaultSecretStore,
    prior_cost: dict[str, tuple[float, float]],
) -> dict[str, Any]:
    client = ccxt_client(entry, store=vault)
    with client.guard():
        balance = client.fetch_balance()
        open_orders, recent_trades, fees_usd = _fetch_cex_extras(client, entry.id)
    tickers, changes = _resolve_ticker_map(
        client,
        balance if isinstance(balance, dict) else {},
        frozenset(entry.usd_aliases),
        entry.quote_currency,
    )
    holdings, total_usd = holdings_from_ccxt_balance(
        balance if isinstance(balance, dict) else {},
        tickers,
        usd_aliases=frozenset(entry.usd_aliases),
        quote_currency=entry.quote_currency,
        prior_cost_basis=prior_cost,
        honest_cost_basis=True,
    )
    return {
        "exchange": entry.id,
        "brand": entry.brand,
        "holdings": holdings,
        "total_usd": round(total_usd, 2),
        "changes": changes,
        "open_orders": open_orders,
        "recent_trades": recent_trades,
        "fees_usd": fees_usd,
    }


def _alpaca_get(base_url: str, path: str, kid: str, sec: str) -> Any:
    req = urllib.request.Request(
        f"{base_url}{path}",
        headers={
            "APCA-API-KEY-ID": kid,
            "APCA-API-SECRET-KEY": sec,
            "Accept": "application/json",
        },
        method="GET",
    )
    with urllib.request.urlopen(req, timeout=20) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _sync_alpaca(kid: str, sec: str) -> dict[str, Any]:
    bases = (
        ["https://api.alpaca.markets", "https://paper-api.alpaca.markets"]
        if kid.upper().startswith("AK")
        else ["https://paper-api.alpaca.markets", "https://api.alpaca.markets"]
    )
    account: dict[str, Any] | None = None
    positions: list[dict[str, Any]] = []
    for base in bases:
        try:
            acc = _alpaca_get(base, "/v2/account", kid, sec)
            if isinstance(acc, dict):
                account = acc
                pos = _alpaca_get(base, "/v2/positions", kid, sec)
                if isinstance(pos, list):
                    positions = [p for p in pos if isinstance(p, dict)]
                break
        except Exception:
            continue
    if account is None:
        raise RuntimeError("Alpaca account fetch failed.")
    holdings: list[HoldingRow] = []
    changes: dict[str, float] = {}
    cash = float(account.get("cash") or 0.0)
    if cash > 0:
        holdings.append(HoldingRow("USD", cash, 1.0, cash, cash))
    for p in positions:
        sym = normalize_asset(str(p.get("symbol") or ""))
        qty = float(p.get("qty") or 0.0)
        price = float(p.get("current_price") or 0.0)
        val = float(p.get("market_value") or (qty * price))
        cost = float(p.get("cost_basis") or val)
        if qty > 0:
            holdings.append(HoldingRow(sym, qty, price, val, cost))
            if p.get("change_today") is not None:
                try:
                    changes[sym] = round(float(p["change_today"]) * 100.0, 2)
                except (TypeError, ValueError):
                    pass
    total = float(account.get("equity") or sum(h.value_usd for h in holdings))
    return {
        "exchange": "alpaca",
        "brand": "Alpaca",
        "holdings": holdings,
        "total_usd": round(total, 2),
        "changes": changes,
        "open_orders": [],
        "recent_trades": [],
        "fees_usd": 0.0,
    }


def _build_backfill_curve(total_usd: float) -> list[dict[str, Any]]:
    """Anchor a 30-day flat mark-to-market baseline on Day 1 until daily snapshots accumulate."""
    today = datetime.now().astimezone().date()
    return [
        {
            "date": (today - timedelta(days=d)).isoformat(),
            "total_usd": round(total_usd, 2),
        }
        for d in range(29, -1, -1)
    ]


def _set_layout_live(root: Path) -> None:
    layout_path = root / "shell_dashboard_layout.json"
    existing: dict[str, Any] = {}
    if layout_path.is_file():
        try:
            loaded = json.loads(layout_path.read_text(encoding="utf-8"))
            if isinstance(loaded, dict):
                existing = loaded
        except Exception:
            existing = {}
    existing["demo"] = False
    layout_path.write_text(json.dumps(existing, indent=2), encoding="utf-8")


def run_live_portfolio_sync(root: Path) -> dict[str, Any]:
    """Sync all CredMan/env-configured exchanges + Alpaca into portfolio.db."""
    root.mkdir(parents=True, exist_ok=True)
    vault = VaultSecretStore()
    vault.bind_registry()
    set_secret_store(vault)

    keyed_cex = [e for e in list_portfolio_exchanges() if e.has_api_keys(vault)]
    alpaca_creds = resolve_alpaca_credentials()
    if not keyed_cex and alpaca_creds is None:
        return {
            "ok": False,
            "error": "no_keys",
            "message": "No exchange API keys configured yet. Click 'Connect Exchange' to add your keys.",
        }

    store = PortfolioStore(root / "portfolio.db", create=True)
    prior_by_venue: dict[str, dict[str, tuple[float, float]]] = {}
    for entry in keyed_cex:
        acc_id = store.get_or_create_account(entry.id, "default")
        prev = store.latest_snapshot(acc_id)
        cmap: dict[str, tuple[float, float]] = {}
        if prev:
            for ph in prev.get("holdings") or []:
                pa = normalize_asset(str(ph.get("asset") or ""))
                pq = float(ph.get("quantity") or 0.0)
                pc = float(ph.get("cost_basis_usd") or 0.0)
                if pa and pq > 0 and pc > 0:
                    cmap[pa] = (pq, pc)
        prior_by_venue[entry.id] = cmap

    venue_results: list[dict[str, Any]] = []
    venue_errors: dict[str, str] = {}
    with ThreadPoolExecutor(max_workers=max(1, min(4, len(keyed_cex) + 1))) as pool:
        futures = {
            pool.submit(_sync_single_cex, entry, vault, prior_by_venue[entry.id]): entry.brand
            for entry in keyed_cex
        }
        if alpaca_creds is not None:
            futures[pool.submit(_sync_alpaca, alpaca_creds[0], alpaca_creds[1])] = "Alpaca"
        for fut in as_completed(futures):
            brand = futures[fut]
            try:
                venue_results.append(fut.result())
            except Exception as exc:
                venue_errors[brand] = str(exc)[:180]

    if not venue_results:
        return {
            "ok": False,
            "error": "sync_failed",
            "venue_errors": venue_errors,
            "message": "All configured exchange syncs failed: "
            + "; ".join(f"{k}: {v}" for k, v in venue_errors.items()),
        }

    today = _local_date_str()
    asset_changes_24h: dict[str, float] = {}
    open_orders: list[dict[str, Any]] = []
    recent_trades: list[dict[str, Any]] = []
    fees_paid_usd = 0.0
    venues_synced: list[str] = []

    for res in venue_results:
        eid = str(res["exchange"])
        acc_id = store.get_or_create_account(eid, "default")
        store.set_account_meta(acc_id, "broker" if eid == "alpaca" else "spot")
        holdings: list[HoldingRow] = res["holdings"]
        total = float(res["total_usd"])
        store.insert_snapshot(acc_id, total, holdings, source=f"{eid}-api")
        unreal = round(sum(h.value_usd - h.cost_basis_usd for h in holdings), 2)
        aggs = store.list_daily_aggregates(acc_id, limit=2)
        prev_total = (
            float(aggs[0]["total_usd"]) if aggs and str(aggs[0]["date"]) != today else total
        )
        daily_pnl = round(total - prev_total, 2)
        store.upsert_daily_aggregate(acc_id, today, total, daily_pnl, 0.0, unreal)
        venues_synced.append(str(res["brand"]))
        asset_changes_24h.update(res.get("changes") or {})
        open_orders.extend(res.get("open_orders") or [])
        recent_trades.extend(res.get("recent_trades") or [])
        fees_paid_usd += float(res.get("fees_usd") or 0.0)

    agg = aggregate_holdings(store)
    net_worth = float(agg.get("total_usd") or 0.0)
    extras = {
        "captured_at": _utc_iso(),
        "venues_synced": sorted(venues_synced),
        "venue_errors": venue_errors,
        "asset_changes_24h": asset_changes_24h,
        "open_orders": open_orders[:50],
        "recent_trades": recent_trades[:50],
        "fees_paid_usd": round(fees_paid_usd, 4),
        "backfill_curve": _build_backfill_curve(net_worth),
    }
    (root / EXTRAS_FILE).write_text(json.dumps(extras, indent=2), encoding="utf-8")
    _set_layout_live(root)

    return {
        "ok": True,
        "venues_synced": sorted(venues_synced),
        "venue_errors": venue_errors,
        "total_usd": net_worth,
        "holdings_count": len(agg.get("holdings") or []),
        "captured_at": extras["captured_at"],
        "message": f"Synced {len(venues_synced)} venue(s) · ${net_worth:,.2f} across {len(agg.get('holdings') or [])} asset(s).",
    }
