"""Guided download/join of Kraken official OHLCVT full-pack parts."""

from __future__ import annotations

import urllib.error
import urllib.request
from collections.abc import Callable
from pathlib import Path

OHLCVT_ASSET_BASE = "https://assets.kraken.com/marketing/institutions/"
OHLCVT_PART_NAMES: tuple[str, ...] = tuple(f"Kraken_OHLCVT_Full.zip.part{i:02d}" for i in range(5))
OHLCVT_JOINED_NAME = "Kraken_OHLCVT_Full.zip"
# Published reassembled SHA-256 (Kraken support article).
OHLCVT_JOINED_SHA256 = "bc273e9027470b07d790a7fa4df9bb43f0dfc527c20c6ecae48402e123e7b1c7"
# Cloudflare rejects the default Python-urllib User-Agent (HTTP 403).
_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)

ProgressCb = Callable[[str, float], None]


def default_download_dir(device_root: Path) -> Path:
    """Prefer ``Price Data`` under the device root (user-facing market archive)."""
    return Path(device_root) / "Price Data"


def discover_joined_archive(device_root: Path) -> Path | None:
    """Return ``Price Data/Kraken_OHLCVT_Full.zip`` when present."""
    joined = default_download_dir(device_root) / OHLCVT_JOINED_NAME
    return joined if joined.is_file() and joined.stat().st_size > 0 else None


def part_urls() -> tuple[str, ...]:
    return tuple(f"{OHLCVT_ASSET_BASE}{name}" for name in OHLCVT_PART_NAMES)


def download_full_archive(
    dest_dir: Path,
    *,
    on_progress: ProgressCb | None = None,
    cancel: Callable[[], bool] | None = None,
) -> Path:
    """Download 5 parts, join into ``Kraken_OHLCVT_Full.zip``, return path."""
    dest_dir = Path(dest_dir)
    dest_dir.mkdir(parents=True, exist_ok=True)
    n_parts = len(OHLCVT_PART_NAMES)
    part_paths: list[Path] = []

    def _emit(msg: str, overall: float) -> None:
        if on_progress is not None:
            on_progress(msg, max(0.0, min(1.0, overall)))

    for i, (name, url) in enumerate(zip(OHLCVT_PART_NAMES, part_urls(), strict=True)):
        if cancel is not None and cancel():
            raise RuntimeError("OHLCVT download cancelled")
        target = dest_dir / name
        label = f"Part {i + 1}/{n_parts}"

        def _part_cb(msg: str, frac: float, *, _i: int = i, _label: str = label) -> None:
            # Reserve 0–90% for parts; 90–100% for join.
            overall = ((_i + max(0.0, min(1.0, frac))) / n_parts) * 0.9
            _emit(f"{_label}: {msg}", overall)

        _download_file(url, target, on_progress=_part_cb, label="downloading")
        part_paths.append(target)
        _emit(f"{label}: done", ((i + 1) / n_parts) * 0.9)

    joined = dest_dir / OHLCVT_JOINED_NAME
    _emit("Joining ZIP parts…", 0.92)
    _join_parts(part_paths, joined)
    _emit("OHLCVT archive ready", 1.0)
    return joined


def _download_file(
    url: str,
    target: Path,
    *,
    on_progress: ProgressCb | None,
    label: str,
) -> None:
    if target.is_file() and target.stat().st_size > 0:
        if on_progress is not None:
            on_progress("cached", 1.0)
        return
    tmp = target.with_suffix(target.suffix + ".partial")
    if tmp.is_file():
        tmp.unlink()
    req = urllib.request.Request(url, headers={"User-Agent": _USER_AGENT})
    total = 0
    done = 0
    # Long timeout: each part is ~2GB; keep-alive reads can idle briefly.
    try:
        with urllib.request.urlopen(req, timeout=600) as resp, tmp.open("wb") as out:
            total = int(resp.headers.get("Content-Length") or 0)
            last_pct = -1
            while True:
                block = resp.read(1024 * 1024)
                if not block:
                    break
                out.write(block)
                done += len(block)
                if on_progress is not None and total > 0:
                    pct = int((done * 100) // total)
                    if pct != last_pct:
                        last_pct = pct
                        mb = done // (1024 * 1024)
                        total_mb = total // (1024 * 1024)
                        on_progress(f"{mb}/{total_mb}MB", done / total)
                elif on_progress is not None and total <= 0 and done % (16 * 1024 * 1024) == 0:
                    on_progress(f"{done // (1024 * 1024)}MB", 0.0)
    except urllib.error.HTTPError as exc:
        if tmp.is_file():
            tmp.unlink(missing_ok=True)
        raise RuntimeError(f"HTTP {exc.code} fetching {target.name}: {exc.reason}") from exc
    if total > 0 and done != total:
        tmp.unlink(missing_ok=True)
        raise RuntimeError(f"incomplete download {target.name}: got {done} of {total} bytes")
    tmp.replace(target)
    if on_progress is not None:
        on_progress("saved", 1.0)


def _join_parts(parts: list[Path], dest: Path) -> None:
    with dest.open("wb") as out:
        for part in parts:
            with part.open("rb") as src:
                while True:
                    block = src.read(1024 * 1024)
                    if not block:
                        break
                    out.write(block)
