from pathlib import Path

import pytest

from trendalgo.market.types import OhlcvPoint
from trendalgo.scanner.config import ScannerSettings
from trendalgo.scanner.live_market import LiveMarketRow, fetch_live_market
from trendalgo.scanner.pipeline import run_pipeline
from trendalgo.scanner.store import ScannerStore
from trendalgo.scanner.watchlist_bridge import pairs_for_bot_whitelist


def test_pipeline_produces_opportunities() -> None:
    snap = run_pipeline(ScannerSettings())
    assert snap.opportunities
    assert snap.opportunities[0].pair
    assert snap.as_of
    assert snap.degraded is True


def test_watchlist_bridge_pins_first(tmp_path: Path) -> None:
    store = ScannerStore(tmp_path / "scanner.db")
    snap = run_pipeline(ScannerSettings())
    store.save_snapshot(snap)
    store.pin_pair("ETH/USD")
    whitelist = pairs_for_bot_whitelist(store, limit=3)
    assert whitelist[0] == "ETH/USD"
    assert len(whitelist) <= 3


def test_pipeline_serves_last_successful_snapshot_when_live_fetch_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    store = ScannerStore(tmp_path / "scanner.db")
    successful = run_pipeline(ScannerSettings(), sample=True).model_copy(
        update={"degraded": False}
    )
    saved_id = store.save_snapshot(successful)
    monkeypatch.delenv("TRENDALGO_MARKET_SOURCE", raising=False)

    def fail_fetch(_pairs: list[str]) -> list[LiveMarketRow]:
        raise TimeoutError("market request exceeded deadline")

    degraded = run_pipeline(ScannerSettings(), store=store, fetcher=fail_fetch)

    assert degraded.degraded is True
    assert degraded.scan_id == saved_id
    assert degraded.as_of == successful.as_of
    assert degraded.opportunities == successful.opportunities


def test_pipeline_uses_synthetic_only_without_successful_cache(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    store = ScannerStore(tmp_path / "scanner.db")
    monkeypatch.delenv("TRENDALGO_MARKET_SOURCE", raising=False)

    def fail_fetch(_pairs: list[str]) -> list[LiveMarketRow]:
        raise ConnectionError("Kraken unavailable")

    degraded = run_pipeline(ScannerSettings(), store=store, fetcher=fail_fetch)

    assert degraded.degraded is True
    assert degraded.scan_id == 0
    assert degraded.opportunities


def test_live_fetch_retries_with_ten_second_request_deadline(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    attempts: list[int] = []

    def flaky_fetch(*_args: object, timeout_ms: int, **_kwargs: object) -> list[OhlcvPoint]:
        attempts.append(timeout_ms)
        if len(attempts) < 3:
            raise TimeoutError("temporary timeout")
        return [
            OhlcvPoint(time=1_700_000_000 + i * 300, open=100, high=102, low=99, close=101, volume=10)
            for i in range(25)
        ]

    monkeypatch.setattr("trendalgo.scanner.live_market.fetch_ohlcv", flaky_fetch)
    monkeypatch.setattr("trendalgo.scanner.live_market.time.sleep", lambda _delay: None)

    rows = fetch_live_market(["BTC/USD"])

    assert len(rows) == 1
    assert attempts == [10_000, 10_000, 10_000]
