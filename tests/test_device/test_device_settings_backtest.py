"""Settings and backtest form rules, and the plain-language result text."""

from __future__ import annotations

import pytest

from trendalgo.device.backtest_model import (
    missing_candles_text,
    summary_rows,
    validate_request,
)
from trendalgo.device.profile import ProfileError
from trendalgo.device.settings_model import (
    Settings,
    settings_from_document,
    settings_to_document,
    validate_settings,
)


def test_a_valid_owner_and_an_empty_host_pass() -> None:
    settings, problems = validate_settings(" owner-1 ", "")
    assert problems == []
    assert settings == Settings("owner-1", "")


@pytest.mark.parametrize(
    ("owner", "host", "message"),
    [
        ("bad owner!", "", "Owner ID:"),
        ("", "", "Owner ID:"),
        ("owner-1", "http://plain.example", "Host address:"),
        ("owner-1", "https://", "Host address:"),
        ("owner-1", "https://host.example:99999", "Host address:"),
    ],
)
def test_bad_settings_are_refused_with_the_field_named(owner: str, host: str, message: str) -> None:
    settings, problems = validate_settings(owner, host)
    assert settings is None
    assert any(p.startswith(message) for p in problems)


def test_a_full_https_host_passes() -> None:
    settings, problems = validate_settings("owner-1", "https://host.example:8443")
    assert problems == []
    assert settings is not None and settings.host_url == "https://host.example:8443"


def test_settings_round_trip_through_the_document_form() -> None:
    settings = Settings("owner-1", "https://host.example")
    assert settings_from_document(settings_to_document(settings)) == settings
    assert settings_from_document(None) is None


def test_a_settings_document_with_bad_content_raises() -> None:
    with pytest.raises(ProfileError, match="settings.json has a value that is not valid"):
        settings_from_document({"owner_id": "bad owner!", "host_url": ""})


def test_a_valid_backtest_request_normalizes_the_pair() -> None:
    request, problems = validate_request(
        pair="eth/usd",
        timeframe="4h",
        indicator="SMA Crossover",
        trailing_stop="0",
    )
    assert problems == []
    assert request is not None
    assert (request.pair, request.timeframe, request.trailing_stop_pct) == ("ETH/USD", "4h", 0.0)


def test_a_backtest_request_names_every_bad_field() -> None:
    request, problems = validate_request(
        pair="nope",
        timeframe="1d",
        indicator="ADX",
        trailing_stop="0.5",
    )
    assert request is None
    assert [p.split(":")[0] for p in problems] == [
        "Pair",
        "Timeframe",
        "Indicator",
        "Trailing stop",
    ]


def test_summary_rows_format_the_numbers_for_people() -> None:
    rows = summary_rows(
        {"final_equity": 1234.5, "net_pct": 1.5, "total_trades": 3, "win_pct": 66.66},
    )
    assert rows == [
        ("Final equity", "$1,234.50"),
        ("Net return", "+1.50%"),
        ("Trades", "3"),
        ("Win rate", "66.7%"),
    ]


def test_missing_candles_text_says_what_is_missing_and_what_the_app_does_not_do() -> None:
    text = missing_candles_text("BTC/USD", "1h")
    assert "No 1h candles for BTC/USD" in text
    assert "does not download them" in text
