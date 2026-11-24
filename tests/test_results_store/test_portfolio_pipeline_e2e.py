"""End-to-end tests for the Portfolio pipeline (PF6-01..04)."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from trendalgo.device.secrets_vault import VaultEntry, memory_vault_for_tests
from trendalgo.exchanges.asset_mapper import normalize_asset
from trendalgo.exchanges.base import holdings_from_ccxt_balance
from trendalgo.exchanges.private_client import SerializedExchange, ccxt_client, set_secret_store
from trendalgo.exchanges.registry import get_entry
from trendalgo.portfolio.report_export import (
    export_portfolio_csv_bundle,
    export_portfolio_html_report,
)
from trendalgo.results_store.desk_dashboard import apply_dashboard_layout, load_dashboard_surface
from trendalgo.results_store.desk_exchange_keys import (
    load_exchange_keys_surface,
    verify_saved_exchange_key,
)
from trendalgo.results_store.desk_portfolio_sync import run_live_portfolio_sync
from trendalgo.results_store.desk_share import share_dashboard_png


def test_kraken_staked_and_legacy_asset_normalization() -> None:
    assert normalize_asset("ZUSD") == "USD"
    assert normalize_asset("XXBT") == "BTC"
    assert normalize_asset("SOL.S") == "SOL"
    assert normalize_asset("ETH2.S") == "ETH"
    assert normalize_asset("USDC.M") == "USDC"
    assert normalize_asset("XXDG") == "DOGE"

    holdings, total = holdings_from_ccxt_balance(
        {"total": {"SOL": 2.0, "SOL.S": 3.0, "ZUSD": 100.0}},
        {"SOL/USD": {"last": 150.0}},
        honest_cost_basis=True,
    )
    by_asset = {h.asset: h for h in holdings}
    assert by_asset["SOL"].quantity == pytest.approx(5.0)
    assert by_asset["SOL"].value_usd == pytest.approx(750.0)
    # Honest cost basis: no fake 0.92 multiplier on initial import
    assert by_asset["SOL"].cost_basis_usd == pytest.approx(750.0)
    assert total == pytest.approx(850.0)


def test_okx_passphrase_and_coinbase_pem_newline_normalization(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    vault, _mem = memory_vault_for_tests()
    vault.bind_registry()
    vault.write_entry(
        VaultEntry(
            exchange_id="okx",
            api_key="okx-k",
            api_secret="okx-s",
            scope="query",
            passphrase="okx-passphrase",
        )
    )
    vault.write_entry(
        VaultEntry(
            exchange_id="coinbaseadvanced",
            api_key="cb-k",
            api_secret="-----BEGIN EC PRIVATE KEY-----\\nabc\\n-----END EC PRIVATE KEY-----",
            scope="query",
        )
    )

    seen_configs: dict[str, dict[str, Any]] = {}

    class _FakeCcxt:
        def __init__(self, cfg: dict[str, Any]) -> None:
            seen_configs[cfg.get("apiKey", "")] = cfg

        def nonce(self) -> int:
            return 1

    import ccxt

    monkeypatch.setattr(ccxt, "okx", _FakeCcxt)
    monkeypatch.setattr(ccxt, "coinbase", _FakeCcxt)

    ccxt_client(get_entry("okx"), store=vault)
    ccxt_client(get_entry("coinbaseadvanced"), store=vault)

    assert seen_configs["okx-k"]["password"] == "okx-passphrase"
    assert "\n" in seen_configs["cb-k"]["secret"]
    assert "\\n" not in seen_configs["cb-k"]["secret"]


class _MockLiveExchange:
    def __init__(self, quote: str, balances: dict[str, float], price_map: dict[str, float]) -> None:
        self._quote = quote
        self._balances = balances
        self._price_map = price_map

    def nonce(self) -> int:
        return 1_700_000_000_000

    def fetch_balance(self) -> dict[str, Any]:
        return {"total": dict(self._balances)}

    def fetch_tickers(self) -> dict[str, Any]:
        return {
            f"{sym}/{self._quote}": {"last": px, "percentage": 2.5}
            for sym, px in self._price_map.items()
        }

    def fetch_open_orders(self) -> list[dict[str, Any]]:
        return [
            {
                "symbol": f"BTC/{self._quote}",
                "side": "buy",
                "type": "limit",
                "price": 60000.0,
                "amount": 0.05,
            }
        ]

    def fetch_my_trades(self, limit: int = 25) -> list[dict[str, Any]]:
        del limit
        return [
            {
                "symbol": f"BTC/{self._quote}",
                "side": "buy",
                "price": 62000.0,
                "amount": 0.1,
                "cost": 6200.0,
                "fee": {"cost": 9.3},
                "datetime": "2026-11-24T12:00:00Z",
            }
        ]


def test_live_sync_dashboard_payload_and_reports_e2e(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    vault, _mem = memory_vault_for_tests()
    vault.bind_registry()
    vault.write_entry(
        VaultEntry(
            exchange_id="kraken",
            api_key="kr-key",
            api_secret="kr-sec",
            scope="query",
        )
    )
    vault.write_entry(
        VaultEntry(
            exchange_id="coinbaseadvanced",
            api_key="cb-key",
            api_secret="cb-sec",
            scope="query",
        )
    )
    set_secret_store(vault)

    # Mock VaultSecretStore() inside desk_exchange_keys & desk_portfolio_sync
    monkeypatch.setattr(
        "trendalgo.results_store.desk_exchange_keys.VaultSecretStore",
        lambda: vault,
    )
    monkeypatch.setattr(
        "trendalgo.results_store.desk_portfolio_sync.VaultSecretStore",
        lambda: vault,
    )
    monkeypatch.setattr(
        "trendalgo.results_store.desk_portfolio_sync.resolve_alpaca_credentials",
        lambda: None,
    )
    monkeypatch.setattr(
        "trendalgo.results_store.desk_exchange_keys.resolve_alpaca_credentials",
        lambda: None,
    )
    monkeypatch.setattr(
        "trendalgo.results_store.desk_exchange_keys.has_alpaca_credentials",
        lambda: False,
    )

    def _fake_client(entry: Any, store: Any = None) -> SerializedExchange:
        del store
        if entry.id == "kraken":
            inner = _MockLiveExchange(
                "USD", {"XXBT": 0.25, "SOL.S": 10.0, "ZUSD": 500.0}, {"BTC": 80_000.0, "SOL": 200.0}
            )
        else:
            inner = _MockLiveExchange("USD", {"ETH": 2.0, "USDC": 1000.0}, {"ETH": 3_000.0})
        return SerializedExchange(inner, exchange_id=entry.id)

    monkeypatch.setattr("trendalgo.results_store.desk_exchange_keys.ccxt_client", _fake_client)
    monkeypatch.setattr("trendalgo.results_store.desk_portfolio_sync.ccxt_client", _fake_client)

    inv = load_exchange_keys_surface(tmp_path)
    assert inv["ok"] is True
    assert inv["configured_count"] == 2

    ver = verify_saved_exchange_key(tmp_path, "kraken")
    assert ver["ok"] is True
    assert ver["nonzero_assets"] == 3

    sync_res = run_live_portfolio_sync(tmp_path)
    assert sync_res["ok"] is True
    assert sync_res["holdings_count"] == 5
    # Kraken: 0.25*80k + 10*200 + 500 = 22,500; Coinbase: 2*3k + 1000 = 7,000 => 29,500
    assert sync_res["total_usd"] == pytest.approx(29_500.0, rel=1e-3)
    assert (tmp_path / "portfolio_live_extras.json").is_file()

    # Dashboard Overview
    dash = load_dashboard_surface(tmp_path)
    assert dash["demo"] is False
    assert dash["has_data"] is True
    assert dash["net_worth_usd"] == pytest.approx(29_500.0, rel=1e-3)
    tiles_by_id = {t["id"]: t for t in dash["tiles"]}
    assert tiles_by_id["total_worth"]["visual_kind"] == "hero_worth"
    assert tiles_by_id["assets"]["visual_kind"] == "holdings_table"
    assert len(tiles_by_id["assets"]["holdings_rows"]) == 5

    # Switch to Analytics page & verify charts
    apply_dashboard_layout(tmp_path, {"active_page_id": "analytics", "range": "3M"})
    analytics_dash = load_dashboard_surface(tmp_path)
    a_tiles = {t["id"]: t for t in analytics_dash["tiles"]}
    assert a_tiles["heatmap"]["visual_kind"] == "treemap"
    assert len(a_tiles["heatmap"]["cells"]) == 5

    # Executive HTML Report
    html_path = export_portfolio_html_report(tmp_path)
    html_text = html_path.read_text(encoding="utf-8")
    assert "TrendAlgo Executive Portfolio Report" in html_text
    assert "$29,500.00" in html_text
    assert "<svg" in html_text
    assert "kr-sec" not in html_text

    # CSV bundle
    csvs = export_portfolio_csv_bundle(tmp_path, dest_dir=tmp_path / "exports")
    assert Path(csvs["holdings_csv"]).is_file()
    assert Path(csvs["equity_csv"]).is_file()

    # 2x High-DPI Dashboard PNG
    pytest.importorskip("PySide6")
    png_res = share_dashboard_png(tmp_path)
    png_path = Path(png_res["path"])
    assert png_path.is_file()
    assert png_path.stat().st_size > 10_000

    # Ensure JSON-serializable
    assert json.dumps(dash)
    set_secret_store(None)
