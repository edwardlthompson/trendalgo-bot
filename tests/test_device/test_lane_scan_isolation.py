"""Per-desk scan stores + lane job gate."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

from trendalgo.device.lane_scan_job import AlpacaKeysRequiredError, lane_scan_job
from trendalgo.device.lts_scan_model import (
    lane_data_file,
    load_lts_rows,
    save_lts_rows,
)
from trendalgo.device.scan_lock import opportunity_scan_lock
from trendalgo.device.scan_model import scan_store_path
from trendalgo.scanner.snapshot import OpportunityRow, QualifiedSnapshot


def test_lane_paths_suffix(tmp_path: Path) -> None:
    assert scan_store_path(tmp_path, "crypto").name == "scanner.db"
    assert scan_store_path(tmp_path, "tradfi").name == "scanner_tradfi.db"
    assert scan_store_path(tmp_path, "forex").name == "scanner_forex.db"
    assert lane_data_file("lts_scan_rows.json", "crypto") == "lts_scan_rows.json"
    assert lane_data_file("lts_scan_rows.json", "tradfi") == "lts_scan_rows_tradfi.json"
    assert opportunity_scan_lock(tmp_path, "tradfi").path.name == "opportunity_scan_tradfi.lock"


def test_lts_rows_do_not_cross_lanes(tmp_path: Path) -> None:
    save_lts_rows(
        tmp_path,
        [{"symbol": "BTC", "pair": "BTC/USD", "exchange_id": "kraken"}],
        lane="crypto",
    )
    save_lts_rows(
        tmp_path,
        [{"symbol": "AAPL", "pair": "AAPL/USD", "exchange_id": "tradfi"}],
        lane="tradfi",
    )
    crypto = load_lts_rows(tmp_path, lane="crypto")
    tradfi = load_lts_rows(tmp_path, lane="tradfi")
    assert crypto and crypto[0]["symbol"] == "BTC"
    assert tradfi and tradfi[0]["symbol"] == "AAPL"
    assert load_lts_rows(tmp_path, lane="forex") == []


def test_lane_scan_job_requires_keys(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "trendalgo.device.lane_scan_job.resolve_alpaca_credentials",
        lambda: None,
    )
    with pytest.raises(AlpacaKeysRequiredError):
        lane_scan_job(tmp_path, "tradfi")


def test_forex_scan_refuses_synthetic_on_alpaca_deny(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from trendalgo.device.lane_scan_filters import LaneScanFilters, save_lane_scan_filters
    from trendalgo.device.lane_scan_job import AlpacaForexDataDeniedError
    from trendalgo.market.types import OhlcvPoint

    monkeypatch.setattr(
        "trendalgo.device.lane_scan_job.resolve_alpaca_credentials",
        lambda: ("PK", "SK"),
    )
    monkeypatch.setattr(
        "trendalgo.device.lane_scan_job.load_forex_universe",
        lambda: ("EUR/USD", "GBP/USD"),
    )
    save_lane_scan_filters(tmp_path, "forex", LaneScanFilters(0.0, 0.0))
    save_lts_rows(
        tmp_path,
        [{"symbol": "EUR", "pair": "EUR/USD", "exchange_id": "forex"}],
        lane="forex",
    )

    def _boom(*_a: Any, **_k: Any) -> list[OhlcvPoint]:
        raise RuntimeError("HTTP Error 403: Forbidden")

    monkeypatch.setattr(
        "trendalgo.market.alpaca_forex.fetch_alpaca_forex_rates",
        _boom,
    )
    with pytest.raises(AlpacaForexDataDeniedError):
        lane_scan_job(tmp_path, "forex")
    assert load_lts_rows(tmp_path, lane="forex") == []


def test_tradfi_scan_job_writes_lane_store(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from trendalgo.device.lane_scan_filters import LaneScanFilters, save_lane_scan_filters
    from trendalgo.market.types import OhlcvPoint

    monkeypatch.setattr(
        "trendalgo.device.lane_scan_job.resolve_alpaca_credentials",
        lambda: ("PK", "SK"),
    )
    monkeypatch.setattr(
        "trendalgo.device.lane_scan_job.load_tradfi_universe",
        lambda *a, **k: ("AAPL", "MSFT", "PENNY"),
    )
    monkeypatch.setattr(
        "trendalgo.device.lane_scan_job.enrich_lane_coins_1h",
        lambda _r, coins, **_k: coins,
    )
    save_lane_scan_filters(
        tmp_path,
        "tradfi",
        LaneScanFilters(min_adv_usd=1_000_000.0, min_price=0.0),
    )

    def _bars(sym: str) -> list[OhlcvPoint]:
        now = int(datetime.now(tz=UTC).timestamp())
        vol = 50_000.0 if sym != "PENNY" else 1.0
        return [
            OhlcvPoint(
                time=now - 86400 * 30,
                open=100,
                high=110,
                low=90,
                close=100,
                volume=vol,
            ),
            OhlcvPoint(time=now, open=100, high=120, low=95, close=110, volume=vol),
        ]

    def _multi(symbols: list[str], *_a: Any, **_k: Any) -> dict[str, list[OhlcvPoint]]:
        return {s: _bars(s) for s in symbols}

    bt_calls: list[int] = []

    def _merge(
        rows: list[dict[str, Any]], root: Path
    ) -> tuple[list[dict[str, Any]], dict[str, Any]]:
        bt_calls.append(len(rows))
        out = []
        for r in rows:
            c = dict(r)
            c["best_strategy"] = "demo"
            c["bot_vs_bh_pct"] = 1.5
            out.append(c)
        return out, {"ok": True, "n": len(rows)}

    monkeypatch.setattr(
        "trendalgo.device.lane_scan_job.fetch_alpaca_equity_bars_multi",
        _multi,
    )
    monkeypatch.setattr(
        "trendalgo.device.lane_scan_job._merge_pass1_backtests",
        _merge,
    )
    result = lane_scan_job(tmp_path, "tradfi")
    assert result["pairs"] == 2  # PENNY filtered by ADV
    assert result["lane"] == "tradfi"
    assert bt_calls == [2]  # All-TA only on survivors
    rows = load_lts_rows(tmp_path, lane="tradfi")
    assert {r["symbol"] for r in rows} == {"AAPL", "MSFT"}
    assert any(r.get("best_strategy") == "demo" for r in rows)
    assert load_lts_rows(tmp_path, lane="crypto") == []
    assert scan_store_path(tmp_path, "tradfi").is_file()


def test_scanner_page_tradfi_does_not_load_crypto(
    tmp_path: Path,
    qtbot: Any,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import os

    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    pytest.importorskip("PySide6")
    from trendalgo.device.context import open_context
    from trendalgo.device.profile import DATA_ENV
    from trendalgo.device.views.scanner_page import ScannerPage

    monkeypatch.setenv(DATA_ENV, str(tmp_path / "data"))
    ctx = open_context(tmp_path / "profile")
    snap = QualifiedSnapshot(
        generated_at=datetime.now(tz=UTC),
        as_of=datetime.now(tz=UTC),
        scan_id=1,
        opportunities=[
            OpportunityRow(
                rank=1,
                pair="BTC/USD",
                uniformity=0.9,
                gain_pct=0.1,
                volume_score=1.0,
                entry_signal=True,
            )
        ],
    )
    save_lts_rows(
        ctx.root,
        [
            {
                "symbol": "BTC",
                "pair": "BTC/USD",
                "exchange_id": "kraken",
                "gains": {"7d": 1, "30d": 1},
            }
        ],
        lane="crypto",
    )
    # Also plant a crypto scanner.db path that TF must ignore
    from trendalgo.device.db import enable_wal
    from trendalgo.device.scan_model import scan_store_path as ssp
    from trendalgo.scanner.store import ScannerStore

    path = ssp(ctx.root, "crypto")
    enable_wal(path)
    ScannerStore(path).save_snapshot(snap)

    monkeypatch.setattr(
        "trendalgo.device.alpaca_vault.has_alpaca_credentials",
        lambda: False,
    )
    # Force CTA path even under pytest env.
    monkeypatch.setattr(
        "trendalgo.device.views.scanner_page.ScannerPage._needs_alpaca_cta",
        lambda self: True,
    )
    page = ScannerPage(ctx, lane="tradfi")
    qtbot.addWidget(page)
    page.show()
    page.reload()
    assert page._coins == []
    assert not page._empty.isHidden()
    assert page._empty.button.isVisible()
    assert page._empty.button.text() == "Set up Alpaca…"
    assert not hasattr(page, "_alpaca_btn")
