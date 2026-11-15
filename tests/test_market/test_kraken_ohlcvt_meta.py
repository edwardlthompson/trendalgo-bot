"""OHLCVT MANIFEST coverage + rolling-ready / mix dates."""

from __future__ import annotations

import json
import zipfile
from datetime import date
from pathlib import Path

from trendalgo.market.kraken_ohlcvt_copy import format_ohlcvt_status, format_subhour_mix_note
from trendalgo.market.kraken_ohlcvt_meta import (
    bands_can_mix,
    mix_allowed,
    read_archive_coverage,
    rolling_bands_ready,
    rolling_ready_date,
)


def _zip_with_manifest(tmp_path: Path, *, end: str = "2026-09-30") -> Path:
    zpath = tmp_path / "Kraken_OHLCVT_Full.zip"
    body = {
        "coverage": {"start": "2013-09-11", "end": end},
        "generated": "2026-10-01",
    }
    with zipfile.ZipFile(zpath, "w") as zf:
        zf.writestr("MANIFEST.json", json.dumps(body))
        zf.writestr("XBTUSD_1.csv", "1,1,1,1,1,1,1\n")
    return zpath


def test_read_archive_coverage_from_zip(tmp_path: Path) -> None:
    zpath = _zip_with_manifest(tmp_path)
    cov = read_archive_coverage(zpath)
    assert cov is not None
    assert cov.start == date(2013, 9, 11)
    assert cov.end == date(2026, 9, 30)


def test_rolling_ready_date_is_start_plus_30() -> None:
    assert rolling_ready_date(date(2026, 11, 15)) == date(2026, 12, 15)
    assert rolling_bands_ready(date(2026, 11, 15), today=date(2026, 12, 14)) is False
    assert rolling_bands_ready(date(2026, 11, 15), today=date(2026, 12, 15)) is True


def test_mix_note_shows_rolling_ready_and_archive_end(tmp_path: Path) -> None:
    zpath = _zip_with_manifest(tmp_path, end="2026-09-30")
    cov = read_archive_coverage(zpath)
    today = date(2026, 11, 15)
    started = date(2026, 11, 15)
    note = format_subhour_mix_note(cov, journal_started=started, today=today)
    assert "2026-09-30" in note
    assert "2026-12-15" in note
    assert "2026-11-15" in note
    assert bands_can_mix(cov, today=today) is False
    assert mix_allowed(cov, journal_started=started, today=today) is False
    status = format_ohlcvt_status(cov, journal_started=started, today=today)
    assert "2026-09-30" in status
    assert "2026-12-15" in status


def test_bands_can_mix_when_archive_catches_today(tmp_path: Path) -> None:
    zpath = _zip_with_manifest(tmp_path, end="2026-11-15")
    cov = read_archive_coverage(zpath)
    today = date(2026, 11, 15)
    assert bands_can_mix(cov, today=today) is True
    note = format_subhour_mix_note(cov, journal_started=today, today=today)
    assert "may activate together" in note.lower()


def test_mix_allowed_via_rolling_journal(tmp_path: Path) -> None:
    zpath = _zip_with_manifest(tmp_path, end="2026-09-30")
    cov = read_archive_coverage(zpath)
    started = date(2026, 11, 15)
    today = date(2026, 12, 15)
    assert mix_allowed(cov, journal_started=started, today=today) is True
    note = format_subhour_mix_note(cov, journal_started=started, today=today)
    assert "may activate together" in note.lower()
    status = format_ohlcvt_status(cov, journal_started=started, today=today)
    assert "may activate together" in status.lower()
    missing_status = format_ohlcvt_status(None, journal_started=started, today=today)
    assert "2026-12-15" in missing_status
    note_missing = format_subhour_mix_note(None, journal_started=started, today=date(2026, 11, 15))
    assert "2026-12-15" in note_missing
