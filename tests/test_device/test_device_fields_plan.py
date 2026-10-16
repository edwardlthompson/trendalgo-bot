"""Field rules and plan logic: validation, the plan version, and a bundle the host accepts."""

from __future__ import annotations

from pathlib import Path

import pytest

from trendalgo.botd.bundle import verify_bundle
from trendalgo.device.fields import check_pair, check_trailing_stop, parse_number
from trendalgo.device.plan_model import (
    BotSpec,
    build_bundle,
    check_plan,
    load_plan,
    next_plan_version,
    plan_document,
    validate_bot,
)
from trendalgo.device.profile import ProfileError, read_json, write_json


def test_parse_number_accepts_commas_and_refuses_non_finite_text() -> None:
    assert parse_number(" 1,000.5 ") == 1000.5
    assert parse_number("abc") is None
    assert parse_number("nan") is None
    assert parse_number("inf") is None


def test_check_pair_normalizes_case_and_refuses_bad_shapes() -> None:
    assert check_pair("btc/usd") == "BTC/USD"
    assert check_pair(" BTC/USDT ") == "BTC/USDT"
    assert check_pair("BTCUSD") is None
    assert check_pair("A/B") is None


def test_check_trailing_stop_allows_zero_or_one_to_twenty() -> None:
    assert check_trailing_stop("0") == 0.0
    assert check_trailing_stop("-0") == 0.0
    assert check_trailing_stop("1") == 1.0
    assert check_trailing_stop("20") == 20.0
    assert check_trailing_stop("0.5") is None
    assert check_trailing_stop("20.1") is None


def _valid_fields(**overrides: str) -> dict[str, str]:
    fields = {
        "name": "Alpha",
        "pair": "btc/usd",
        "timeframe": "1h",
        "indicator": "RSI",
        "stake": "250",
        "trailing_stop": "5",
    }
    fields.update(overrides)
    return fields


def test_a_valid_bot_becomes_a_spec_with_a_normalized_pair() -> None:
    spec, problems = validate_bot(**_valid_fields())
    assert problems == []
    assert spec == BotSpec("Alpha", "BTC/USD", "1h", "RSI", 250.0, 5.0)


def test_each_bad_field_gets_its_own_plain_message() -> None:
    spec, problems = validate_bot(
        **_valid_fields(name=" ", pair="x", timeframe="1d", indicator="", stake="0"),
    )
    assert spec is None
    assert [p.split(":")[0] for p in problems] == [
        "Name",
        "Pair",
        "Timeframe",
        "Indicator",
        "Stake",
    ]


def test_a_stake_above_the_cap_and_a_stop_of_zero_are_checked() -> None:
    spec, problems = validate_bot(**_valid_fields(stake="100001"))
    assert spec is None and problems[0].startswith("Stake:")
    spec, problems = validate_bot(**_valid_fields(trailing_stop="0"))
    assert problems == [] and spec is not None and spec.trailing_stop_pct == 0.0


def test_plan_checks_need_a_bot_unique_names_and_a_cap() -> None:
    assert check_plan([]) == ["Add at least one bot before saving the plan."]
    alpha = BotSpec("Alpha", "BTC/USD", "1h", "RSI", 100.0, 5.0)
    twin = BotSpec("alpha", "ETH/USD", "1h", "RSI", 100.0, 5.0)
    assert check_plan([alpha, twin]) == ["Each bot needs a different name."]
    many = [BotSpec(f"Bot {i}", "BTC/USD", "1h", "RSI", 1.0, 0.0) for i in range(21)]
    assert check_plan(many) == ["A plan holds at most 20 bots."]


def test_each_save_raises_the_plan_version() -> None:
    assert next_plan_version(0) == 1
    assert next_plan_version(7) == 8


def test_a_built_bundle_passes_the_hosts_own_verifier() -> None:
    spec = BotSpec("Alpha", "BTC/USD", "1h", "RSI", 250.0, 5.0)
    bundle = build_bundle([spec], owner_id="owner-1", plan_version=3)
    verified = verify_bundle(bundle["header"], bundle["payload"], host_owner_id="owner-1")
    assert verified.plan_version == 3
    assert verified.publisher == "owner"


def test_a_bundle_for_another_owner_is_refused_by_the_host_check() -> None:
    from trendalgo.botd.owner import ForeignOwnerError

    spec = BotSpec("Alpha", "BTC/USD", "1h", "RSI", 250.0, 5.0)
    bundle = build_bundle([spec], owner_id="owner-1", plan_version=1)
    with pytest.raises(ForeignOwnerError):
        verify_bundle(bundle["header"], bundle["payload"], host_owner_id="someone-else")


def test_a_saved_plan_loads_back_unchanged(tmp_path: Path) -> None:
    spec = BotSpec("Alpha", "BTC/USD", "4h", "MACD", 500.0, 0.0)
    target = tmp_path / "plan.json"
    write_json(target, plan_document(4, [spec]))
    assert load_plan(read_json(target)) == (4, [spec])


def test_no_plan_file_means_version_zero_and_no_bots() -> None:
    assert load_plan(None) == (0, [])


@pytest.mark.parametrize(
    "document",
    [
        {"plan_version": "x", "bots": []},
        {"plan_version": -1, "bots": []},
        {"plan_version": 1, "bots": "nope"},
        {"plan_version": 1, "bots": ["not a bot"]},
        {"plan_version": 1, "bots": [{"name": "A", "pair": "??"}]},
    ],
)
def test_a_malformed_plan_file_is_refused_not_guessed(document: dict[str, object]) -> None:
    with pytest.raises(ProfileError, match="plan.json has a bot that is not valid"):
        load_plan(document)
