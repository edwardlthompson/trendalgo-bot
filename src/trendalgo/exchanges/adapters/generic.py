"""Generic CCXT read-only portfolio adapter (S14)."""

from __future__ import annotations

from typing import Any

from trendalgo.exchanges.adapters.fixtures import DRY_RUN_HOLDINGS
from trendalgo.exchanges.asset_mapper import normalize_asset
from trendalgo.exchanges.base import holdings_from_ccxt_balance
from trendalgo.exchanges.private_client import ccxt_client
from trendalgo.exchanges.registry import ExchangeEntry
from trendalgo.portfolio.db import HoldingRow, PortfolioStore
from trendalgo.trading.order_journal_store import default_journal
from trendalgo.trading.reconcile import reconcile_exchange


class GenericCcxtPortfolioAdapter:
    """Registry-driven adapter — works for any CCXT exchange with portfolio_enabled."""

    def __init__(self, entry: ExchangeEntry) -> None:
        self.entry = entry
        self.exchange_id = entry.id

    def _usd_aliases(self) -> frozenset[str]:
        return frozenset(self.entry.usd_aliases)

    def _client(self) -> Any:
        return ccxt_client(self.entry)

    def _normalize_holdings(self, holdings: list[HoldingRow]) -> list[HoldingRow]:
        return [
            HoldingRow(
                asset=normalize_asset(h.asset),
                quantity=h.quantity,
                price_usd=h.price_usd,
                value_usd=h.value_usd,
                cost_basis_usd=h.cost_basis_usd,
            )
            for h in holdings
        ]

    def sync_balances(self, store: PortfolioStore, *, dry_run: bool = True) -> dict[str, Any]:
        account_id = store.get_or_create_account(self.exchange_id, "default")
        store.set_account_meta(account_id, "spot")

        if dry_run:
            from trendalgo.portfolio.stress_fixture import stress_holdings_for_exchange

            stress = stress_holdings_for_exchange(self.exchange_id)
            if stress:
                holdings = self._normalize_holdings(stress)
            elif self.exchange_id == "kraken":
                from trendalgo.portfolio.performance import current_btc_holding

                holdings = self._normalize_holdings([current_btc_holding()])
            else:
                holdings = self._normalize_holdings(
                    DRY_RUN_HOLDINGS.get(
                        self.exchange_id,
                        [
                            HoldingRow(
                                asset="USD",
                                quantity=100.0,
                                price_usd=1.0,
                                value_usd=100.0,
                                cost_basis_usd=100.0,
                            ),
                        ],
                    )
                )
            total = sum(h.value_usd for h in holdings)
            snap_id = store.insert_snapshot(
                account_id, total, holdings, source=f"dry-run-{self.exchange_id}"
            )
            return {
                "account_id": account_id,
                "snapshot_id": snap_id,
                "total_usd": total,
                "holdings": len(holdings),
                "mode": "dry-run",
                "exchange": self.exchange_id,
            }

        exchange = self._client()
        journal = default_journal()
        with exchange.guard():  # no order of ours is sent while the account is read (E3)
            try:
                report = reconcile_exchange(journal, exchange, self.exchange_id)
                balance = report.balance
                reconcile_result: dict[str, Any] = {
                    "open": len(report.open),
                    "unresolved": len(report.unresolved),
                    "halted": report.halt_reason,
                }
            except Exception as exc:  # the snapshot still shows holdings; buys stay gated
                balance = exchange.fetch_balance()
                reconcile_result = {"error": str(exc)}
        reason = journal.pending_halt_notice(self.exchange_id)  # a halt from any path (E3)
        if reason is not None:
            store.insert_notification("trading", f"{self.exchange_id}: new buys halted", reason)
            journal.mark_halt_announced(self.exchange_id)
        try:
            raw_tickers = exchange.fetch_tickers()
            tickers: dict[str, Any] = dict(raw_tickers) if isinstance(raw_tickers, dict) else {}
        except Exception:
            tickers = {}

        usd_all = frozenset({*self._usd_aliases(), "USD", "ZUSD", "USDT", "USDC"})
        quote = self.entry.quote_currency.strip().upper() or "USD"
        for raw_asset, qty in (balance.get("total") or {}).items():
            try:
                if float(qty or 0) <= 0:
                    continue
            except (TypeError, ValueError):
                continue
            sym = normalize_asset(str(raw_asset))
            if sym in usd_all or sym.startswith("USD"):
                continue
            if any(
                isinstance(tickers.get(f"{sym}/{q}"), dict)
                and tickers[f"{sym}/{q}"].get("last") is not None
                for q in (quote, "USD", "USDT", "USDC")
            ):
                continue
            for q in (quote, "USD", "USDT", "USDC"):
                pair = f"{sym}/{q}"
                try:
                    t = exchange.fetch_ticker(pair)
                except Exception:
                    continue
                if isinstance(t, dict) and t.get("last") is not None:
                    tickers[pair] = t
                    break

        prior_cost: dict[str, tuple[float, float]] = {}
        prev_snap = store.latest_snapshot(account_id)
        if prev_snap:
            for prev_h in prev_snap.get("holdings") or []:
                pa = normalize_asset(str(prev_h.get("asset") or ""))
                pq = float(prev_h.get("quantity") or 0.0)
                pc = float(prev_h.get("cost_basis_usd") or 0.0)
                if pa and pq > 0 and pc > 0:
                    prior_cost[pa] = (pq, pc)

        holdings, total_usd = holdings_from_ccxt_balance(
            balance,
            tickers,
            usd_aliases=self._usd_aliases(),
            quote_currency=self.entry.quote_currency,
            prior_cost_basis=prior_cost,
            honest_cost_basis=True,
        )
        holdings = self._normalize_holdings(holdings)
        snap_id = store.insert_snapshot(
            account_id,
            round(total_usd, 2),
            holdings,
            source=f"{self.exchange_id}-api",
        )
        return {
            "account_id": account_id,
            "snapshot_id": snap_id,
            "total_usd": round(total_usd, 2),
            "holdings": len(holdings),
            "mode": "live",
            "exchange": self.exchange_id,
            "reconcile": reconcile_result,
        }
