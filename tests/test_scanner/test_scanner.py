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
    successful = run_pipeline(ScannerSettings(), sample=True).model_copy(update={"degraded": False})
    saved_id = store.save_snapshot(successful)
    monkeypatch.delenv("TRENDALGO_MARKET_SOURCE", raising=False)

    def fail_fetch(_pairs: list[str]) -> list[LiveMarketRow]:
        raise TimeoutError("market request exceeded deadline")

    reused = run_pipeline(ScannerSettings(), store=store, fetcher=fail_fetch)

    assert reused.degraded is False
    assert reused.scan_id == saved_id
    assert reused.as_of == successful.as_of
    assert reused.opportunities == successful.opportunities


def test_pipeline_raises_without_successful_cache_when_live_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import trendalgo.scanner.listings as listings

    store = ScannerStore(tmp_path / "scanner.db")
    monkeypatch.delenv("TRENDALGO_MARKET_SOURCE", raising=False)
    listings._CACHE = None
    monkeypatch.setattr(
        listings,
        "_fetch_kraken_usd_spot",
        lambda: list(listings.DEFAULT_KRAKEN_SPOT),
    )

    def fail_fetch(_pairs: list[str]) -> list[LiveMarketRow]:
        raise ConnectionError("Kraken unavailable")

    with pytest.raises(RuntimeError, match="Kraken market data"):
        run_pipeline(ScannerSettings(), store=store, fetcher=fail_fetch)


def test_live_fetch_retries_with_request_deadline(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    attempts: list[int] = []
    base = 1_700_000_000

    def flaky_fetch(
        _pair: object,
        timeframe: str,
        *_args: object,
        timeout_ms: int,
        **_kwargs: object,
    ) -> list[OhlcvPoint]:
        attempts.append(timeout_ms)
        if len(attempts) < 2:
            raise TimeoutError("temporary timeout")
        n = 40 if timeframe == "1d" else 200
        step = 86_400 if timeframe == "1d" else 3600
        return [
            OhlcvPoint(
                time=base + i * step,
                open=100,
                high=102,
                low=99,
                close=101 + i * 0.01,
                volume=10_000,
            )
            for i in range(n)
        ]

    monkeypatch.setattr("trendalgo.scanner.live_market.fetch_ohlcv", flaky_fetch)
    monkeypatch.setattr("trendalgo.scanner.live_market.time.sleep", lambda _delay: None)
    monkeypatch.setattr(
        "trendalgo.scanner.live_market.fetch_quote_volumes",
        lambda pairs, **_k: {},
    )

    rows = fetch_live_market(["BTC/USD"], require_continuous_1h=False)

    assert len(rows) == 1
    # Fail once on first 1h call, then 1h + 1d succeed (no 5m stage).
    assert attempts[0] == 12_000
    assert len(attempts) >= 3
    assert rows[0].volume_usd > 0
