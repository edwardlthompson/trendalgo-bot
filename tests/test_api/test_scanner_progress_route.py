"""GET /api/v1/scanner/progress — live run state with an ``after`` poll cursor."""

from __future__ import annotations

from fastapi.testclient import TestClient

from trendalgo.api.app import create_app
from trendalgo.api.state import default_state
from trendalgo.scanner.progress import get_scan_progress


def test_progress_route_returns_state_and_only_newer_events() -> None:
    client = TestClient(create_app(default_state()))
    progress = get_scan_progress()
    progress.begin_job("Scan")
    try:
        progress.log("route smoke line")
        body = client.get("/api/v1/scanner/progress", params={"after": 0}).json()
        assert body["state"]["active"] is True
        assert any(event["message"] == "route smoke line" for event in body["events"])

        cursor = body["last_seq"]
        newer = client.get("/api/v1/scanner/progress", params={"after": cursor}).json()
        assert all(event["seq"] > cursor for event in newer["events"])
    finally:
        progress.end_job()


def test_progress_route_rejects_negative_cursor() -> None:
    client = TestClient(create_app(default_state()))
    response = client.get("/api/v1/scanner/progress", params={"after": -1})
    assert response.status_code == 422
