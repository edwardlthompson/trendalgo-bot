"""Device scan rules (D-02): pure helpers the page and the job share. No Qt, no network, no threads.

The scan itself runs in a worker (`scan_job.py`). This module says which settings a device scan uses,
where its results are kept, what counts as unavailable, and what the status line shows.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from trendalgo.device.lts_scan_model import load_filters
from trendalgo.device.profile import SCANNER_DB
from trendalgo.scanner.config import ScannerSettings, default_scanner_settings


class ScanUnavailableError(RuntimeError):
    """Kraken's pair list or market data was missing. No scan is saved, so no fallback data is shown."""


def device_scan_settings(root: Path | None = None) -> ScannerSettings:
    """Defaults, with optional filter overrides saved on this PC (min volume, min gain, interval)."""
    base = default_scanner_settings()
    if root is None:
        return base
    saved = load_filters(root)
    if not saved:
        return base
    payload = base.model_dump()
    if "min_volume_usd" in saved:
        payload["min_volume_usd"] = float(saved["min_volume_usd"])
    # Scan gate uses the 30d floor. Fall back to legacy min_gain_pct.
    gain_key = "min_gain_30d" if "min_gain_30d" in saved else "min_gain_pct"
    if gain_key in saved:
        # UI stores percent (30); ScannerSettings uses a fraction (0.30).
        gain = float(saved[gain_key])
        payload["min_gain_pct"] = gain / 100.0 if gain > 1 else gain
    if "min_gain_7d" in saved:
        gain7 = float(saved["min_gain_7d"])
        payload["min_gain_7d_pct"] = gain7 / 100.0 if gain7 > 1 else gain7
    if "min_uniformity" in saved:
        payload["min_uniformity"] = float(saved["min_uniformity"])
    if "interval_minutes" in saved:
        payload["interval_minutes"] = int(saved["interval_minutes"])
    return ScannerSettings.model_validate(payload)


def scan_store_path(root: Path) -> Path:
    """This PC's scanner database. It sits in the profile folder, never in the shared data folder."""
    return root / SCANNER_DB


def progress_line(progress: dict[str, Any] | None) -> str:
    """One status line: the phase, its count, and the latest message. Empty when there is nothing yet."""
    if not progress:
        return ""
    state = _progress_state(progress)
    parts: list[str] = []
    phase = str(state.get("phase") or "")
    if phase:
        parts.append(phase)
    total = int(state.get("step_total") or 0)
    if total > 0:
        done = int(state.get("step_done") or 0)
        unit = str(state.get("step_unit") or "")
        parts.append(f"{done} of {total} {unit}".rstrip())
    message = str(progress.get("message") or "")
    if message:
        parts.append(message)
    return " · ".join(parts)


def progress_pct(progress: dict[str, Any] | None) -> int | None:
    """0–100 for a progress bar, or None when step totals are unknown."""
    if not progress:
        return None
    state = _progress_state(progress)
    total = int(state.get("step_total") or 0)
    if total <= 0:
        # Pair-scan style payloads use top-level done/total.
        total = int(progress.get("total") or 0)
        done = int(progress.get("done") or 0)
    else:
        done = int(state.get("step_done") or 0)
    if total <= 0:
        return None
    return min(100, max(0, int(100 * done / total)))


def _progress_state(progress: dict[str, Any]) -> dict[str, Any]:
    raw_state = progress.get("state")
    return raw_state if isinstance(raw_state, dict) else {}
