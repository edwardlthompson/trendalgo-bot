"""Append-only JSONL execution & timing log for scans, backtests, benchmarks, and trades."""

from __future__ import annotations

import json
import time
from datetime import datetime
from pathlib import Path

LOG_FILE = "execution_logs.jsonl"
_MAX_LINES = 500
_TRIM_AT = 600


def append_execution_log(
    root: Path,
    *,
    kind: str,
    lane: str,
    summary: str,
    total_s: float,
    stages: dict[str, float] | None = None,
    pair: str = "",
) -> None:
    """Append one timing/execution record to ``root / execution_logs.jsonl``."""
    try:
        root.mkdir(parents=True, exist_ok=True)
        path = root / LOG_FILE
        clean_stages: dict[str, float] = {}
        if stages:
            for k, v in stages.items():
                try:
                    clean_stages[str(k)] = round(float(v), 3)
                except (TypeError, ValueError):
                    continue
        entry = {
            "ts": int(time.time()),
            "iso": datetime.now().astimezone().isoformat(timespec="seconds"),
            "kind": kind,
            "lane": lane,
            "pair": pair,
            "total_s": round(max(0.0, float(total_s)), 3),
            "stages": clean_stages,
            "summary": summary,
        }
        with path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(entry, separators=(",", ":")) + "\n")
        _trim_if_needed(path)
    except Exception:  # noqa: BLE001 — telemetry must never break jobs
        pass


def _trim_if_needed(path: Path) -> None:
    lines = path.read_text(encoding="utf-8").splitlines()
    if len(lines) > _TRIM_AT:
        path.write_text("\n".join(lines[-_MAX_LINES:]) + "\n", encoding="utf-8")
