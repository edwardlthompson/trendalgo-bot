from pathlib import Path

from trendalgo.scanner.config import ScannerSettings
from trendalgo.scanner.pipeline import run_pipeline
from trendalgo.scanner.store import ScannerStore
from trendalgo.scanner.watchlist_bridge import pairs_for_bot_whitelist


def test_pipeline_produces_opportunities() -> None:
    snap = run_pipeline(ScannerSettings())
    assert snap.opportunities
    assert snap.opportunities[0].pair


def test_watchlist_bridge_pins_first(tmp_path: Path) -> None:
    store = ScannerStore(tmp_path / "scanner.db")
    snap = run_pipeline(ScannerSettings())
    store.save_snapshot(snap)
    store.pin_pair("ETH/USD")
    whitelist = pairs_for_bot_whitelist(store, limit=3)
    assert whitelist[0] == "ETH/USD"
    assert len(whitelist) <= 3
