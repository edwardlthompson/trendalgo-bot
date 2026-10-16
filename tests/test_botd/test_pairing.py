"""W-PAIR: pairing codes are single-use, expire after 10 minutes, and are stored only as hashes."""

from __future__ import annotations

from pathlib import Path

from trendalgo.botd.host_store import HostStore
from trendalgo.botd.pairing import CODE_ALPHABET, PAIRING_TTL_S, PairingCodes

NOW = 1_800_000_000


def _codes(tmp_path: Path) -> tuple[PairingCodes, HostStore]:
    store = HostStore(tmp_path / "host.db")
    return PairingCodes(store), store


def _row_count(store: HostStore) -> int:
    with store.connect() as conn:
        return int(conn.execute("SELECT COUNT(*) FROM pairing_codes").fetchone()[0])


def test_an_issued_code_uses_only_the_unambiguous_alphabet(tmp_path: Path) -> None:
    codes, _ = _codes(tmp_path)
    code = codes.issue(NOW)
    assert len(code) == 9 and code[4] == "-"
    assert all(char in CODE_ALPHABET for char in code.replace("-", ""))
    assert not set("01OI") & set(code)


def test_a_code_redeems_exactly_once(tmp_path: Path) -> None:
    codes, _ = _codes(tmp_path)
    code = codes.issue(NOW)
    assert codes.redeem(code, NOW) is True
    assert codes.redeem(code, NOW) is False


def test_redeeming_accepts_the_code_typed_without_dash_or_in_lower_case(tmp_path: Path) -> None:
    codes, _ = _codes(tmp_path)
    code = codes.issue(NOW)
    assert codes.redeem(code.replace("-", " ").lower(), NOW) is True


def test_a_wrong_code_is_refused(tmp_path: Path) -> None:
    codes, _ = _codes(tmp_path)
    code = codes.issue(NOW)
    wrong = "AAAA-AAAA" if code != "AAAA-AAAA" else "BBBB-BBBB"
    assert codes.redeem(wrong, NOW) is False
    assert codes.redeem(code, NOW) is True


def test_a_code_is_valid_up_to_its_expiry_and_refused_after(tmp_path: Path) -> None:
    codes, _ = _codes(tmp_path)
    on_time = codes.issue(NOW)
    late = codes.issue(NOW)
    assert codes.redeem(on_time, NOW + PAIRING_TTL_S) is True
    assert codes.redeem(late, NOW + PAIRING_TTL_S + 1) is False


def test_issuing_prunes_codes_that_have_expired(tmp_path: Path) -> None:
    codes, store = _codes(tmp_path)
    codes.issue(NOW)
    assert _row_count(store) == 1
    codes.issue(NOW + PAIRING_TTL_S + 1)
    assert _row_count(store) == 1


def test_the_plaintext_code_is_never_written_to_disk(tmp_path: Path) -> None:
    codes, store = _codes(tmp_path)
    code = codes.issue(NOW)
    assert code.replace("-", "").encode() not in store.db_path.read_bytes()
