from trendalgo.lts.adapter import LtsAdapter, OhlcvBar


def test_normalize_bars() -> None:
    adapter = LtsAdapter("BTC/USD")
    rows = [[1_700_000_000_000, 100.0, 101.0, 99.0, 100.5, 12.0]]
    bars = adapter.normalize_bars(rows)
    assert len(bars) == 1
    assert bars[0] == OhlcvBar(1_700_000_000_000, 100.0, 101.0, 99.0, 100.5, 12.0)


def test_is_ready_native_port() -> None:
    assert LtsAdapter().is_ready() is True
