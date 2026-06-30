"""Bot P/L summary enrichment tests."""

from __future__ import annotations

from pathlib import Path

from trendalgo.bots.summary import bot_pnl_breakdown, enrich_bots
from trendalgo.risk.journal import TradeJournal, TradeRecord


def _append_bot_trade(
    journal: TradeJournal,
    bot_id: int,
    side: str,
    *,
    stake: float,
    pnl: float = 0.0,
    created_at: str = "2026-06-01T12:00:00+00:00",
) -> None:
    journal.append_trade(
        TradeRecord(
            pair="BTC/USD",
            side=side,
            stake_usd=stake,
            pnl_usd=pnl,
            signal_source="test",
            rationale="unit",
            exchange_trade_id=f"{bot_id}-{side}-{stake}",
            bot_id=bot_id,
        ),
        created_at=created_at,
    )


def test_bot_pnl_breakdown_realized_and_unrealized(tmp_path: Path) -> None:
    journal = TradeJournal(tmp_path / "journal.db")
    bot_id = 7
    _append_bot_trade(journal, bot_id, "buy", stake=100.0, created_at="2026-06-01T10:00:00+00:00")
    _append_bot_trade(
        journal,
        bot_id,
        "sell",
        stake=100.0,
        pnl=12.5,
        created_at="2026-06-01T11:00:00+00:00",
    )
    chart = [{"time": 1, "value": 100.0}, {"time": 2, "value": 110.0}]
    breakdown = bot_pnl_breakdown(journal, bot_id, chart=chart, current_price=110.0)
    assert breakdown["realized_pnl_usd"] == 12.5
    assert breakdown["trade_count"] == 2
    assert breakdown["pnl_usd"] == breakdown["realized_pnl_usd"] + breakdown["unrealized_pnl_usd"]


def test_enrich_bots_adds_pnl_fields(tmp_path: Path) -> None:
    journal = TradeJournal(tmp_path / "journal.db")
    bot_id = 3
    _append_bot_trade(journal, bot_id, "buy", stake=50.0)
    bots = [{"id": bot_id, "pair": "ETH/USD", "equity_usd": 500.0}]
    enriched = enrich_bots(bots, journal, price_by_pair={"ETH/USD": 3000.0})
    assert enriched[0]["trade_count"] == 1
    assert "pnl_pct" in enriched[0]


def test_last_close_for_pair_uses_price_service(tmp_path: Path) -> None:
    from trendalgo.bots.summary import last_close_for_pair
    from trendalgo.market.types import PricePoint

    class FakeService:
        def get_closes(self, pair: str, timeframe: str, since, until) -> list[PricePoint]:
            del pair, timeframe, since, until
            return [PricePoint(time=1, close=123.45)]

    journal = TradeJournal(tmp_path / "journal.db")
    assert last_close_for_pair(journal, "BTC/USD", "1h", FakeService()) == 123.45


def test_enrich_bots_with_market(tmp_path: Path, monkeypatch) -> None:
    from trendalgo.bots.summary import enrich_bots_with_market
    from trendalgo.market.types import PricePoint

    journal = TradeJournal(tmp_path / "journal.db")
    bot_id = 9
    _append_bot_trade(journal, bot_id, "buy", stake=25.0)
    bots = [{"id": bot_id, "pair": "BTC/USD", "timeframe": "1h", "equity_usd": 1000.0}]

    class FakeService:
        def get_closes(self, pair: str, timeframe: str, since, until) -> list[PricePoint]:
            del pair, timeframe, since, until
            return [PricePoint(time=1, close=50_000.0)]

    monkeypatch.setattr(
        "trendalgo.market.service.PriceHistoryService",
        lambda _path: FakeService(),
    )
    enriched = enrich_bots_with_market(bots, journal, tmp_path)
    assert enriched[0]["trade_count"] == 1
