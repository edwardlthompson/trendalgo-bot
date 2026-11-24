"""Persistent stdin/stdout NDJSON sidecar for instant Avalonia UI surface reads."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

from trendalgo.results_store.desk_cli_extra import run_mutate
from trendalgo.results_store.desk_export import export_surface


def handle_request(root: Path, req: dict[str, Any]) -> dict[str, Any]:
    """Dispatch one NDJSON request and return a JSON-serializable response."""
    req_id = req.get("id")
    op = str(req.get("op") or "").strip().lower()
    lane = str(req.get("lane") or "crypto")
    pair = str(req.get("pair") or "")
    try:
        if op == "surface":
            surface = str(req.get("surface") or "")
            data = export_surface(root, surface, lane=lane, pair=pair)
            return {"id": req_id, "ok": True, "data": data}
        if op == "toggle_watch":
            data = run_mutate(root, toggle_watch=True, pair=pair, lane=lane, indicator="RSI")
            return {"id": req_id, "ok": True, "data": data}
        if op == "ping":
            return {"id": req_id, "ok": True, "data": {"pong": True}}
        return {"id": req_id, "ok": False, "error": f"unknown op: {op}"}
    except Exception as exc:  # noqa: BLE001
        return {"id": req_id, "ok": False, "error": f"{type(exc).__name__}: {exc}"}


def run_sidecar(root: Path) -> int:
    """Serve NDJSON requests on stdin until EOF."""
    root.mkdir(parents=True, exist_ok=True)
    for raw in sys.stdin:
        line = raw.strip()
        if not line:
            continue
        try:
            req = json.loads(line)
        except ValueError as exc:
            resp: dict[str, Any] = {"id": None, "ok": False, "error": f"invalid_json: {exc}"}
        else:
            if not isinstance(req, dict):
                resp = {"id": None, "ok": False, "error": "request_not_object"}
            else:
                resp = handle_request(root, req)
        sys.stdout.write(json.dumps(resp, separators=(",", ":")) + "\n")
        sys.stdout.flush()
    return 0
