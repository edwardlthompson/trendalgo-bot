"""Append-only local 1m tip journal bridging OHLCVT archive lag."""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import cast

import pandas as pd

from trendalgo.backtest.load_days import SCAN_LOOKBACK_DAYS, trim_ohlcv_frame

_JOURNAL_KEEP_DAYS = SCAN_LOOKBACK_DAYS + 15
_META_NAME = "journal_meta.json"


def journal_dir(device_root: Path) -> Path:
    return Path(device_root) / "Price Data" / "ohlcvt_journal"


def journal_path(device_root: Path, stem: str) -> Path:
    return journal_dir(device_root) / f"{stem}.pkl"


def load_journal(device_root: Path, stem: str) -> pd.DataFrame | None:
    path = journal_path(device_root, stem)
    if not path.is_file():
        return None
    try:
        frame = pd.read_pickle(path)
    except Exception:
        return None
    if not isinstance(frame, pd.DataFrame) or frame.empty:
        return None
    return frame


def append_tip(device_root: Path, stem: str, tip: pd.DataFrame | None) -> pd.DataFrame | None:
    """Merge tip into journal, keep ~45d, return updated frame."""
    if tip is None or tip.empty or not str(stem).strip():
        return load_journal(device_root, stem)
    existing = load_journal(device_root, stem)
    parts = [p for p in (existing, tip) if p is not None and not p.empty]
    if not parts:
        return None
    merged = cast(pd.DataFrame, pd.concat(parts))
    merged = cast(pd.DataFrame, merged[~merged.index.duplicated(keep="last")].sort_index())
    frame = trim_ohlcv_frame(merged, _JOURNAL_KEEP_DAYS)
    path = journal_path(device_root, stem)
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_pickle(path)
    _ensure_started_meta(device_root, frame)
    return frame


def stitch_with_journal(archive: pd.DataFrame, journal: pd.DataFrame | None) -> pd.DataFrame:
    """Merge journal onto archive (intentional gap bridge; no 2d tip limit)."""
    if journal is None or journal.empty:
        return archive
    if archive is None or archive.empty:
        return journal
    both = cast(pd.DataFrame, pd.concat([archive, journal]))
    return cast(pd.DataFrame, both[~both.index.duplicated(keep="last")].sort_index())


def journal_span_ready(frame: pd.DataFrame | None, *, today: date | None = None) -> bool:
    """True when journal holds ≥30d ending near today."""
    if frame is None or frame.empty:
        return False
    idx = frame.index
    if not isinstance(idx, pd.DatetimeIndex) or len(idx) < 2:
        return False
    day = today or datetime.now(tz=UTC).date()
    end_day = _index_day(idx[-1])
    if end_day is None or end_day < day - timedelta(days=2):
        return False
    span = idx[-1] - idx[0]
    return bool(span >= pd.Timedelta(days=SCAN_LOOKBACK_DAYS))


def read_started(device_root: Path) -> date | None:
    meta = journal_dir(device_root) / _META_NAME
    if not meta.is_file():
        return None
    try:
        import json

        raw = json.loads(meta.read_text(encoding="utf-8"))
        text = str(raw.get("started") or "").strip()
        return date.fromisoformat(text[:10]) if text else None
    except Exception:
        return None


def write_started(device_root: Path, started: date) -> None:
    import json

    path = journal_dir(device_root) / _META_NAME
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"started": started.isoformat()}), encoding="utf-8")


def _index_day(value: object) -> date | None:
    ts = pd.Timestamp(str(value))
    if bool(pd.isna(ts)):
        return None
    if ts.tzinfo is not None:
        ts = ts.tz_convert("UTC")
    return date(int(ts.year), int(ts.month), int(ts.day))


def _ensure_started_meta(device_root: Path, frame: pd.DataFrame) -> None:
    if read_started(device_root) is not None:
        return
    idx = frame.index
    if not isinstance(idx, pd.DatetimeIndex) or idx.empty:
        write_started(device_root, datetime.now(tz=UTC).date())
        return
    day = _index_day(idx[0]) or datetime.now(tz=UTC).date()
    write_started(device_root, day)
