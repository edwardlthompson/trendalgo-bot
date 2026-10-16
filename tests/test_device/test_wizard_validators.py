"""Wizard validators: every refusal carries a stable reason code, and clean input passes."""

from __future__ import annotations

import pytest

from trendalgo.device.wizard.validators import (
    PERMISSIONS,
    REQUIRED_PERMISSIONS,
    check_key_permissions,
    check_loopback_url,
    check_owner_secret,
    check_pairing_code,
    normalize_pairing_code,
)


def test_all_five_permissions_with_withdraw_off_pass() -> None:
    assert check_key_permissions(REQUIRED_PERMISSIONS, True) is None


def test_the_permission_list_matches_the_guide_text() -> None:
    assert PERMISSIONS == (
        "Query Funds",
        "Query Open Orders & Trades",
        "Query Closed Orders & Trades",
        "Modify Orders",
        "Cancel/Close Orders",
    )


def test_withdraw_left_unconfirmed_is_refused_even_with_every_permission() -> None:
    problem = check_key_permissions(REQUIRED_PERMISSIONS, False)
    assert problem is not None
    assert problem.code == "kraken.withdraw_unconfirmed"


def test_a_missing_permission_is_named_in_the_message() -> None:
    ticked = REQUIRED_PERMISSIONS - {"Modify Orders"}
    problem = check_key_permissions(ticked, True)
    assert problem is not None
    assert problem.code == "kraken.permissions_missing"
    assert "Modify Orders" in problem.message


def test_nothing_ticked_names_every_permission() -> None:
    problem = check_key_permissions(frozenset(), True)
    assert problem is not None
    for name in PERMISSIONS:
        assert name in problem.message


@pytest.mark.parametrize("text", ["ABCD-EFGH", "abcd efgh", "ABCDEFGH", " ABCD-EFGH "])
def test_a_typed_pairing_code_passes_the_format_check(text: str) -> None:
    assert check_pairing_code(text) is None


@pytest.mark.parametrize(
    "text", ["", "ABCD-EFG", "ABCD-EFGHJ", "ABCD-EFG0", "ABCD-EFGI", "ABCD-EFGO"]
)
def test_a_mistyped_pairing_code_is_refused_with_a_format_code(text: str) -> None:
    problem = check_pairing_code(text)
    assert problem is not None
    assert problem.code == "pair.code_format"


def test_pairing_codes_normalize_to_upper_case_without_dashes_or_spaces() -> None:
    assert normalize_pairing_code(" ab-cd ef ") == "ABCDEF"


def test_a_good_owner_secret_passes() -> None:
    assert check_owner_secret("x" * 32) is None


def test_a_short_owner_secret_is_refused() -> None:
    problem = check_owner_secret("x" * 31)
    assert problem is not None
    assert problem.code == "owner.secret_short"


def test_an_owner_secret_with_a_space_is_refused_even_when_long_enough() -> None:
    problem = check_owner_secret("x" * 32 + " ")
    assert problem is not None
    assert problem.code == "owner.secret_whitespace"


@pytest.mark.parametrize(
    "url",
    ["http://127.0.0.1:8080", "http://127.0.0.1:1", "http://127.0.0.1:65535/"],
)
def test_the_practice_host_on_loopback_passes(url: str) -> None:
    assert check_loopback_url(url) is None


@pytest.mark.parametrize(
    "url",
    [
        "https://127.0.0.1:8443",
        "https://host.example:8443",
        "http://localhost:8080",
        "http://0.0.0.0:8080",
        "http://127.0.0.1",
        "http://127.0.0.1:notaport",
        "http://127.0.0.1:99999",
        "http://[::1",
        "",
    ],
)
def test_anything_else_is_refused_as_not_loopback(url: str) -> None:
    problem = check_loopback_url(url)
    assert problem is not None
    assert problem.code == "host.not_loopback"
