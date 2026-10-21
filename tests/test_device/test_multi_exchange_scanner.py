"""Multi-exchange scanner: checklist, dual-venue rows, rate meters."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

from trendalgo.device.lts_scan_model import build_lts_rows, filter_coins, normalize_coin
from trendalgo.device.scan_identity import coin_in_watchlist, row_key, watch_key
from trendalgo.device.scan_venues import resolve_scan_exchange_ids, vaulted_scan_venues
from trendalgo.device.secrets_vault import VaultEntry, memory_vault_for_tests
from trendalgo.exchanges.private_budget import (
    acquire_private_slot,
    budget_snapshot,
    reset_budgets,
)
from trendalgo.market.rate_budget import RateBudget
from trendalgo.scanner.snapshot import OpportunityRow, QualifiedSnapshot

pytest.importorskip("pytestqt")
from pytestqt.qtbot import QtBot  # noqa: E402


def _snap(pair: str = "BTC/USD") -> QualifiedSnapshot:
    return QualifiedSnapshot(
        generated_at=datetime.now(UTC),
        as_of=datetime.now(UTC),
        scan_id=1,
        opportunities=[
            OpportunityRow(
                rank=1,
                pair=pair,
                uniformity=0.8,
                gain_pct=0.1,
                volume_score=1_000_000,
                entry_signal=True,
                sparkline=[1.0, 1.1],
            )
        ],
    )


def test_row_key_keeps_same_symbol_on_two_venues_apart() -> None:
    a = normalize_coin({"symbol": "BTC", "pair": "BTC/USD", "exchange_id": "kraken"})
    b = normalize_coin({"symbol": "BTC", "pair": "BTC/USD", "exchange_id": "coinbaseadvanced"})
    assert row_key(a) == "kraken:BTC"
    assert row_key(b) == "coinbaseadvanced:BTC"
    assert row_key(a) != row_key(b)


def test_filter_coins_multi_select_exchanges() -> None:
    coins = [
        normalize_coin({"symbol": "BTC", "listed_on": ["kraken"], "gains": {"7d": 1.0}}),
        normalize_coin({"symbol": "ETH", "listed_on": ["coinbaseadvanced"], "gains": {"7d": 1.0}}),
        normalize_coin({"symbol": "SOL", "listed_on": ["kraken"], "gains": {"7d": 1.0}}),
    ]
    only = filter_coins(coins, exchanges=["kraken"])
    assert [c["symbol"] for c in only] == ["BTC", "SOL"]
    none = filter_coins(coins, exchanges=[])
    assert none == []
    both = filter_coins(coins, exchanges=["kraken", "coinbaseadvanced"])
    assert len(both) == 3


def test_watchlist_keys_are_per_venue() -> None:
    coin = normalize_coin({"symbol": "BTC", "exchange_id": "kraken"})
    other = normalize_coin({"symbol": "BTC", "exchange_id": "coinbaseadvanced"})
    watch = {watch_key("kraken", "BTC")}
    assert coin_in_watchlist(coin, watch)
    assert not coin_in_watchlist(other, watch)


def test_vaulted_scan_venues_requires_keys() -> None:
    vault, _mem = memory_vault_for_tests()
    vault.bind_registry()
    assert vaulted_scan_venues(vault) == []
    vault.write_entry(VaultEntry(exchange_id="kraken", api_key="k", api_secret="s", scope="query"))
    venues = vaulted_scan_venues(vault)
    assert [v.exchange_id for v in venues] == ["kraken"]
    assert resolve_scan_exchange_ids({"scan_exchanges": ["kraken"]}, store=vault) == ["kraken"]
    assert resolve_scan_exchange_ids({"scan_exchanges": ["coinbaseadvanced"]}, store=vault) == []


def test_build_lts_rows_stamps_exchange_id() -> None:
    rows = build_lts_rows(_snap(), enrich_charts=False, exchange_id="coinbaseadvanced")
    assert rows[0]["exchange_id"] == "coinbaseadvanced"
    assert rows[0]["listed_on"] == ["coinbaseadvanced"]


def test_rate_budget_used_remaining_snapshot() -> None:
    budget = RateBudget(3, window_s=60.0)
    assert budget.used(0.0) == 0
    assert budget.remaining(0.0) == 3
    assert budget.try_acquire(0.0)
    assert budget.try_acquire(1.0)
    snap = budget.snapshot(1.0)
    assert snap == {"used": 2, "remaining": 1, "max_calls": 3, "window_s": 60.0}


def test_budget_snapshot_increments() -> None:
    reset_budgets()
    assert budget_snapshot("kraken", max_per_min=5, now=0.0)["used"] == 0
    assert acquire_private_slot("kraken", max_per_min=5)
    assert budget_snapshot("kraken", max_per_min=5)["used"] == 1
    reset_budgets()


def test_exchange_checklist_summary_and_selection(qtbot: QtBot) -> None:
    from trendalgo.device import strings as S
    from trendalgo.device.views.exchange_checklist import ExchangeChecklist

    box = ExchangeChecklist()
    qtbot.addWidget(box)
    box.set_options([("kraken", "Kraken"), ("coinbaseadvanced", "Coinbase")])
    assert box.selected_ids() == ["kraken", "coinbaseadvanced"]
    assert box.text() == S.SCANNER_EXCHANGES_ALL
    box.set_selected_ids(["kraken"])
    assert box.selected_ids() == ["kraken"]
    assert "Kraken" in box.text()
    box.set_options([], selected=[])
    assert box.text() == S.SCANNER_EXCHANGES_NEED_KEYS


def test_scan_job_merges_dual_venue_rows(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from trendalgo.device.scan_job import scan_job
    from trendalgo.exchanges.registry import load_registry

    vault, _mem = memory_vault_for_tests()
    vault.bind_registry()
    for eid in ("kraken", "coinbaseadvanced"):
        vault.write_entry(VaultEntry(exchange_id=eid, api_key="k", api_secret="s", scope="query"))

    def fake_pipeline(settings: Any, entry: Any, *, client: Any = None) -> QualifiedSnapshot:
        return _snap("BTC/USD")

    monkeypatch.setattr("trendalgo.device.scan_job.VaultSecretStore", lambda *a, **k: vault)
    monkeypatch.setattr(
        "trendalgo.device.scan_job.resolve_scan_exchange_ids",
        lambda *_a, **_k: ["kraken", "coinbaseadvanced"],
    )
    monkeypatch.setattr("trendalgo.device.scan_job.run_venue_pipeline", fake_pipeline)
    monkeypatch.setattr("trendalgo.device.scan_job.ccxt_client", lambda *_a, **_k: object())
    monkeypatch.setattr(
        "trendalgo.device.scan_job._merge_pass1_backtests",
        lambda rows, _root: (rows, {}),
    )
    monkeypatch.setattr(
        "trendalgo.device.scan_job.load_filters",
        lambda _root: {"scan_exchanges": ["kraken", "coinbaseadvanced"]},
    )
    assert load_registry().by_id("kraken") is not None

    result = scan_job(tmp_path)
    assert result["rows"] == 2
    assert result["venues"] == ["kraken", "coinbaseadvanced"]
    from trendalgo.device.lts_scan_model import load_lts_rows

    loaded = load_lts_rows(tmp_path)
    keys = {row_key(c) for c in loaded}
    assert keys == {"kraken:BTC", "coinbaseadvanced:BTC"}


def test_scanner_copy_mentions_keyed_venues() -> None:
    from trendalgo.device import strings as S

    assert "API keys" in S.SCANNER_SUBTITLE or "API key" in S.SCANNER_EMPTY_BODY
    assert "API calls this minute" in S.SETTINGS_KEYS_RATE
    assert S.SCANNER_NO_EXCHANGES
