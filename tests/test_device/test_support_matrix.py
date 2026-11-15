"""Honest support matrix + All-TA category coverage."""

from __future__ import annotations

from pathlib import Path

from trendalgo.backtest.ta_fleet import all_strategies
from trendalgo.device import strings as S
from trendalgo.device.support_matrix import (
    about_support_line,
    capability_mark,
    checklist_brand,
    clear_support_matrix_cache,
    load_support_matrix,
    venue_by_id,
)
from trendalgo.device.ta_strategy_categories import (
    categorized_strategy_ids,
    load_strategy_categories,
    render_readme_strategy_details,
)

ROOT = Path(__file__).resolve().parents[2]
README = ROOT / "README.md"
START = "<!-- ta-strategy-categories:start -->"
END = "<!-- ta-strategy-categories:end -->"


def setup_function() -> None:
    clear_support_matrix_cache()


def test_matrix_loads_kraken_full_and_tradfi_coming_soon() -> None:
    venues = load_support_matrix()
    assert venues
    kraken = venue_by_id("kraken")
    assert kraken is not None
    assert kraken.public_scan_ready
    assert kraken.status == "supported"
    assert capability_mark(kraken.public_scan) == "✓"
    tradfi = venue_by_id("tradfi")
    assert tradfi is not None
    assert tradfi.status == "partial"
    assert tradfi.status_label == "Partial"
    assert tradfi.portfolio == "partial"
    assert capability_mark(tradfi.portfolio) == "partial"
    solana = venue_by_id("solana")
    assert solana is not None
    assert solana.status == "partial"
    assert solana.portfolio == "yes"


def test_every_cex_registry_id_has_matrix_row() -> None:
    from trendalgo.exchanges.registry import list_exchanges

    missing = [e.id for e in list_exchanges() if venue_by_id(e.id) is None]
    assert missing == []


def test_coming_soon_venues_never_claim_supported_label() -> None:
    for venue in load_support_matrix():
        if venue.status == "coming_soon":
            assert "Supported" not in venue.status_label
            assert venue.status_label == "Coming soon"


def test_strategy_categories_cover_all_strategies_exactly_once() -> None:
    expected = {s.upper() for s in all_strategies()}
    cats = load_strategy_categories()
    assert cats
    seen: list[str] = []
    for cat in cats:
        assert cat.name
        assert cat.strategies
        seen.extend(cat.strategies)
    assert len(seen) == len(set(seen))
    assert set(seen) == expected
    assert categorized_strategy_ids() == frozenset(expected)


def test_readme_details_block_matches_categories() -> None:
    text = README.read_text(encoding="utf-8")
    assert START in text and END in text
    inner = text.split(START, 1)[1].split(END, 1)[0].strip()
    assert inner == render_readme_strategy_details().strip()
    assert "<details>" in inner
    assert "Candlestick patterns" in inner
    assert "`RSI`" in inner


def test_readme_exchange_table_matches_matrix() -> None:
    from trendalgo.device.support_matrix_readme import (
        END,
        START,
        extract_marked_block,
        render_exchange_support_table,
    )

    text = README.read_text(encoding="utf-8")
    assert START in text and END in text
    inner = extract_marked_block(text)
    assert inner is not None
    assert inner.strip() == render_exchange_support_table().strip()


def test_about_and_checklist_honesty_copy() -> None:
    line = about_support_line()
    assert "Kraken" in line
    assert "Alpaca" in line or "TradFi" in line
    assert "Supported" not in line
    from trendalgo.device.support_matrix import can_keyed_chart_enrich

    assert checklist_brand("kraken", "Kraken") == "Kraken"
    assert "Kraken-depth" in checklist_brand("binanceus", "Binance.US")
    assert can_keyed_chart_enrich("binanceus")
    assert can_keyed_chart_enrich("kraken")
    assert not can_keyed_chart_enrich("tradfi")
    assert "Kraken today" in S.ABOUT_SUPPORT
    assert "DEX" in about_support_line()
    assert "coming soon" in S.SCANNER_RESEARCH_HINT.lower()
