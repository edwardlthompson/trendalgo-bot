"""Pull host portfolio snapshot into local portfolio.db (device holds no keys)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from trendalgo.portfolio.db import HoldingRow, PortfolioStore


def _holding_rows(raw: list[Any]) -> list[HoldingRow]:
    rows: list[HoldingRow] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        rows.append(
            HoldingRow(
                asset=str(item.get("asset") or ""),
                quantity=float(item.get("quantity") or 0.0),
                price_usd=float(item.get("price_usd") or 0.0),
                value_usd=float(item.get("value_usd") or 0.0),
                cost_basis_usd=float(item.get("cost_basis_usd") or 0.0),
            )
        )
    return rows


def host_portfolio_payload(store_path: Path) -> dict[str, Any] | None:
    """Serialize the host-side portfolio.db for the device Sync call."""
    if not store_path.is_file():
        return None
    store = PortfolioStore(store_path, create=False)
    accounts = store.list_accounts()
    if not accounts:
        return None
    account_id = int(accounts[0]["id"])
    for account in accounts:
        if account.get("exchange") == "kraken":
            account_id = int(account["id"])
            break
    snap = store.latest_snapshot(account_id)
    if snap is None:
        return None
    equity = store.list_daily_aggregates(account_id, limit=365)
    return {
        "account": {
            "exchange": str(accounts[0].get("exchange") or "kraken"),
            "label": str(accounts[0].get("label") or "default"),
        },
        "snapshot": {
            "total_usd": float(snap["total_usd"]),
            "holdings": list(snap["holdings"]),
            "captured_at": str(snap["captured_at"]),
            "source": str(snap.get("source") or "host"),
        },
        "equity": [
            {
                "date": str(row["date"]),
                "total_usd": float(row["total_usd"]),
                "daily_pnl_usd": float(row.get("daily_pnl_usd") or 0),
                "realized_usd": float(row.get("realized_usd") or 0),
                "unrealized_usd": float(row.get("unrealized_usd") or 0),
            }
            for row in reversed(equity)
        ],
        "accounts": [
            {
                "exchange": str(a.get("exchange") or ""),
                "label": str(a.get("label") or ""),
                "id": int(a["id"]),
            }
            for a in accounts
        ],
        "tags": store.get_asset_tags(),
    }


def apply_host_portfolio(local_path: Path, payload: dict[str, Any]) -> bool:
    """Write host payload into the device portfolio.db. Returns True when applied."""
    snap = payload.get("snapshot")
    if not isinstance(snap, dict):
        return False
    holdings = snap.get("holdings")
    if not isinstance(holdings, list):
        return False
    raw_account = payload.get("account")
    account_meta: dict[str, Any] = raw_account if isinstance(raw_account, dict) else {}
    exchange = str(account_meta.get("exchange") or "kraken")
    label = str(account_meta.get("label") or "default")
    store = PortfolioStore(local_path, create=True)
    account_id = store.get_or_create_account(exchange, label)
    store.insert_snapshot(
        account_id,
        float(snap.get("total_usd") or 0.0),
        _holding_rows(holdings),
        source=str(snap.get("source") or "host"),
    )
    for point in payload.get("equity") or []:
        if not isinstance(point, dict):
            continue
        day = str(point.get("date") or "")
        if not day:
            continue
        store.upsert_daily_aggregate(
            account_id,
            day,
            float(point.get("total_usd") or 0.0),
            float(point.get("daily_pnl_usd") or 0.0),
            float(point.get("realized_usd") or 0.0),
            float(point.get("unrealized_usd") or 0.0),
        )
    tags = payload.get("tags")
    if isinstance(tags, dict):
        for asset, tag in tags.items():
            try:
                store.set_asset_tag(str(asset), str(tag))
            except Exception:
                continue
    return True
