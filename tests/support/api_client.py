"""Authed TestClient helper — mutating API routes require owner bearer (AUTH-01)."""

from __future__ import annotations

import os
from pathlib import Path

from fastapi.testclient import TestClient

from trendalgo.api.app import create_app
from trendalgo.api.state import AppState, default_state


def make_api_client(state: AppState | None = None) -> TestClient:
    os.environ.setdefault("TRENDALGO_FEE_SYNC_ON_START", "0")
    os.environ.setdefault("TRENDALGO_OWNER_SECRET", "test-owner-secret")
    os.environ.setdefault("TRENDALGO_OWNER_ID", "test-owner")
    if "TRENDALGO_DATA_DIR" not in os.environ:
        import tempfile

        os.environ["TRENDALGO_DATA_DIR"] = str(Path(tempfile.mkdtemp(prefix="trendalgo-api-test-")))
    app_state = state or default_state()
    app = create_app(app_state)
    issued = app_state.bearer_store.mint()
    client = TestClient(app)
    client.headers.update({"Authorization": f"Bearer {issued.token}"})
    return client
