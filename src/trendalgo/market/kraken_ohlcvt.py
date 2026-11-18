"""Kraken OHLCVT archive reader: 1m CSV from ZIP or extracted dir + local cache."""

from __future__ import annotations

import zipfile
from pathlib import Path
from typing import BinaryIO, cast

import pandas as pd

from trendalgo.backtest.load_days import SCAN_LOOKBACK_DAYS, trim_ohlcv_frame

_COLS = ("timestamp", "open", "high", "low", "close", "volume", "trades")
_CACHE_PAD_DAYS = 5


def archive_ready(path: str | Path | None) -> bool:
    root = Path(str(path or "").strip()) if path else None
    if root is None or not root.exists():
        return False
    return (root.is_file() and root.suffix.lower() == ".zip") or root.is_dir()


def ohlcvt_stems(pair: str) -> tuple[str, ...]:
    text = str(pair or "").strip().upper().replace("-", "/")
    if "/" in text:
        base, quote = text.split("/", 1)
    else:
        base, quote = text, "USD"
    bases = [base]
    if base in ("BTC", "XBT", "XXBT"):
        bases = ["XBT", "XXBT", "BTC"]
    elif base in ("ETH", "XETH"):
        bases = ["ETH", "XETH"]
    quotes = [quote, "ZUSD"] if quote == "USD" else [quote]
    out: list[str] = []
    seen: set[str] = set()
    for b in bases:
        for q in quotes:
            stem = f"{b}{q}"
            if stem not in seen:
                seen.add(stem)
                out.append(stem)
    return tuple(out)


def cache_path(cache_dir: Path, stem: str) -> Path:
    return Path(cache_dir) / "ohlcvt" / "1m" / f"{stem}.pkl"


def clear_ohlcvt_caches(cache_dir: Path | None) -> int:
    """Delete cached 1m pickle frames after a new quarterly ZIP is installed."""
    if cache_dir is None:
        return 0
    root = Path(cache_dir) / "ohlcvt" / "1m"
    if not root.is_dir():
        return 0
    n = 0
    for path in root.glob("*.pkl"):
        try:
            path.unlink()
            n += 1
        except OSError:
            continue
    return n


def load_1m_frame(
    *,
    pair: str,
    archive_path: str | Path,
    cache_dir: Path | None = None,
    days: int = SCAN_LOOKBACK_DAYS,
) -> tuple[pd.DataFrame | None, str]:
    """Return last ``days`` of 1m OHLCV from archive (relative to archive end)."""
    if not archive_ready(archive_path):
        return None, "ohlcvt path missing"
    stems = ohlcvt_stems(pair)
    for stem in stems:
        if cache_dir is not None:
            cached = _read_cache(cache_path(cache_dir, stem), days)
            if cached is not None and not cached.empty:
                return cached, stem
        frame = _read_1m_csv(Path(archive_path), stem, days=days + _CACHE_PAD_DAYS)
        if frame is None or frame.empty:
            continue
        frame = reindex_1m(trim_ohlcv_frame(frame, days))
        if cache_dir is not None and not frame.empty:
            _write_cache(cache_path(cache_dir, stem), frame)
        return frame, stem
    return None, f"no *_1.csv for {','.join(stems)}"


def reindex_1m(frame: pd.DataFrame) -> pd.DataFrame:
    if frame is None or frame.empty:
        return frame
    idx = frame.index
    if not isinstance(idx, pd.DatetimeIndex):
        return frame
    full = pd.date_range(idx.min(), idx.max(), freq="1min", tz="UTC")
    out = frame.reindex(full)
    for col in ("open", "high", "low", "close"):
        if col in out.columns:
            out[col] = out[col].ffill()
    if "volume" in out.columns:
        out["volume"] = out["volume"].fillna(0.0)
    return cast(pd.DataFrame, out.dropna(subset=["close"]))


def stitch_live_tip(archive: pd.DataFrame, tip: pd.DataFrame | None) -> pd.DataFrame:
    """Append tip only when it continues near the archive end (no multi-week gap fill)."""
    if tip is None or tip.empty or archive is None or archive.empty:
        return archive
    tip_start = pd.Timestamp(str(tip.index.min()))
    arch_end = pd.Timestamp(str(archive.index.max()))
    if tip_start - arch_end > pd.Timedelta(days=2):
        return archive
    both = cast(pd.DataFrame, pd.concat([archive, tip]))
    return cast(pd.DataFrame, both[~both.index.duplicated(keep="last")].sort_index())


def _read_cache(path: Path, days: int) -> pd.DataFrame | None:
    if not path.is_file():
        return None
    try:
        frame = pd.read_pickle(path)
    except Exception:
        return None
    if not isinstance(frame, pd.DataFrame) or frame.empty:
        return None
    return trim_ohlcv_frame(frame, days)


def _write_cache(path: Path, frame: pd.DataFrame) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_pickle(path)


def _read_1m_csv(root: Path, stem: str, *, days: int) -> pd.DataFrame | None:
    name = f"{stem}_1.csv"
    try:
        if root.is_file() and root.suffix.lower() == ".zip":
            with zipfile.ZipFile(root, "r") as zf:
                member = _find_member(zf, name)
                if member is None:
                    return None
                with zf.open(member) as raw:
                    return _parse_csv_tail(raw, days=days)
        path = root / name if root.is_dir() else None
        if path is None or not path.is_file():
            matches = list(root.rglob(name)) if root.is_dir() else []
            if not matches:
                return None
            path = matches[0]
        with path.open("rb") as raw:
            return _parse_csv_tail(raw, days=days)
    except Exception:
        return None


def _find_member(zf: zipfile.ZipFile, name: str) -> str | None:
    """Exact basename match (avoid AIXBTUSD matching XBTUSD via endswith)."""
    for info in zf.namelist():
        if Path(info).name == name:
            return info
    return None


def _parse_csv_tail(raw: BinaryIO | object, *, days: int) -> pd.DataFrame | None:
    """Keep the last ``days`` of rows relative to the file's newest timestamp."""
    window = max(1, int(days)) * 86_400
    pad = 7 * 86_400
    parts: list[pd.DataFrame] = []
    max_ts = 0
    reader = pd.read_csv(
        cast(BinaryIO, raw),
        header=None,
        names=list(_COLS),
        chunksize=250_000,
        dtype={
            "timestamp": "int64",
            "open": "float64",
            "high": "float64",
            "low": "float64",
            "close": "float64",
            "volume": "float64",
            "trades": "float64",
        },
    )
    for chunk in reader:
        cmax = int(cast(float, chunk["timestamp"].max()))
        max_ts = max(max_ts, cmax)
        cutoff = max_ts - window - pad
        keep = cast(pd.DataFrame, chunk[chunk["timestamp"] >= cutoff])
        if not keep.empty:
            parts.append(keep)
        parts = [p for p in parts if int(cast(float, p["timestamp"].max())) >= cutoff]
    if not parts or max_ts <= 0:
        return None
    frame = cast(pd.DataFrame, pd.concat(parts, ignore_index=True))
    cutoff = max_ts - window - pad
    frame = cast(pd.DataFrame, frame[frame["timestamp"] >= cutoff])
    if frame.empty:
        return None
    idx = pd.to_datetime(frame["timestamp"], unit="s", utc=True)
    out = cast(
        pd.DataFrame, frame.drop(columns=["timestamp", "trades"]).set_index(idx).sort_index()
    )
    out.index.name = "timestamp"
    return cast(pd.DataFrame, out[~out.index.duplicated(keep="last")])
