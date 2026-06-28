"""Top-10 equal-weight benchmark tests."""

from datetime import UTC, datetime

from trendalgo.portfolio.top10_benchmark import (
    TOP10_SYMBOLS,
    compare_to_top10,
    top10_index_curve,
)


def test_top10_index_tracks_portfolio_timestamps() -> None:
    now = int(datetime(2026, 6, 26, 12, 0, tzinfo=UTC).timestamp())
    portfolio = [
        {"time": now - 86_400, "value": 50_000.0},
        {"time": now, "value": 55_000.0},
    ]
    index = top10_index_curve(portfolio)
    assert len(index) == 2
    assert index[0]["time"] == portfolio[0]["time"]


def test_compare_to_top10_alpha() -> None:
    portfolio = [{"time": 1, "value": 100.0}, {"time": 2, "value": 110.0}]
    index = [{"time": 1, "value": 100.0}, {"time": 2, "value": 105.0}]
    cmp_ = compare_to_top10(portfolio, index)
    assert cmp_["portfolio_return_pct"] == 10.0
    assert cmp_["top10_return_pct"] == 5.0
    assert cmp_["alpha_pct"] == 5.0
    assert len(cmp_["symbols"]) == len(TOP10_SYMBOLS)
