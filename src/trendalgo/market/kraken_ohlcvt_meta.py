"""OHLCVT archive coverage (MANIFEST) + mix-unlock dates."""

from __future__ import annotations

import json
import zipfile
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

from trendalgo.backtest.load_days import SCAN_LOOKBACK_DAYS
from trendalgo.market.kraken_ohlcvt import archive_ready


@dataclass(frozen=True)
class ArchiveCoverage:
    start: date | None
    end: date | None


def read_archive_coverage(path: str | Path | None) -> ArchiveCoverage | None:
    """Read coverage.start/end from MANIFEST.json inside a ZIP or folder."""
    if not archive_ready(path):
        return None
    root = Path(str(path).strip())
    try:
        raw = _read_manifest_bytes(root)
        if raw is None:
            return None
        data = json.loads(raw.decode("utf-8"))
        cov = data.get("coverage") if isinstance(data, dict) else None
        if not isinstance(cov, dict):
            return None
        return ArchiveCoverage(
            start=_parse_day(cov.get("start")),
            end=_parse_day(cov.get("end")),
        )
    except Exception:
        return None


def today_utc(*, today: date | None = None) -> date:
    return today or datetime.now(tz=UTC).date()


def rolling_ready_date(started: date) -> date:
    """Calendar day when a tip journal started on ``started`` reaches 30d depth."""
    return started + timedelta(days=SCAN_LOOKBACK_DAYS)


def rolling_bands_ready(started: date | None, *, today: date | None = None) -> bool:
    if started is None:
        return False
    return today_utc(today=today) >= rolling_ready_date(started)


def bands_can_mix(coverage: ArchiveCoverage | None, *, today: date | None = None) -> bool:
    """True when quarterly (or other) archive 1m covers through today."""
    if coverage is None or coverage.end is None:
        return False
    return coverage.end >= today_utc(today=today)


def mix_allowed(
    coverage: ArchiveCoverage | None,
    *,
    journal_started: date | None = None,
    today: date | None = None,
) -> bool:
    """Sub-hour and 1h–24h may activate together via archive catch-up or rolling 30d."""
    return bands_can_mix(coverage, today=today) or rolling_bands_ready(journal_started, today=today)


def _parse_day(raw: object) -> date | None:
    text = str(raw or "").strip()
    if not text:
        return None
    try:
        return date.fromisoformat(text[:10])
    except ValueError:
        return None


def _read_manifest_bytes(root: Path) -> bytes | None:
    if root.is_file() and root.suffix.lower() == ".zip":
        with zipfile.ZipFile(root, "r") as zf:
            for name in zf.namelist():
                if Path(name).name.upper() == "MANIFEST.JSON":
                    return zf.read(name)
        return None
    if root.is_dir():
        for cand in (root / "MANIFEST.json", *root.rglob("MANIFEST.json")):
            if cand.is_file():
                return cand.read_bytes()
    return None
