"""Alpaca assets parser filters warrants/units junk."""

from __future__ import annotations

from trendalgo.brokers.alpaca_assets import is_junk_equity_symbol, parse_tradable_equity_assets


def test_parse_keeps_tradable_drops_junk() -> None:
    rows = [
        {"symbol": "AAPL", "tradable": True, "status": "active", "name": "Apple Inc"},
        {"symbol": "BRK.B", "tradable": True, "status": "active", "name": "Berkshire"},
        {"symbol": "FOOWS", "tradable": True, "status": "active", "name": "Foo Warrant"},
        {"symbol": "ZZZZW", "tradable": True, "status": "active", "name": "Zzz Corp"},
        {"symbol": "DEAD", "tradable": False, "status": "active", "name": "Dead Co"},
        {"symbol": "OLD", "tradable": True, "status": "inactive", "name": "Old Co"},
    ]
    out = parse_tradable_equity_assets(rows)
    assert out == ["AAPL", "BRK.B"]


def test_junk_heuristics() -> None:
    assert is_junk_equity_symbol("ABCWS")
    assert is_junk_equity_symbol("LONGW")
    assert is_junk_equity_symbol("X", name="Acme Warrant Series A")
    assert not is_junk_equity_symbol("AAPL")
    assert not is_junk_equity_symbol("BRK.B")
