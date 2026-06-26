"""Uvicorn entrypoint — `uv run trendalgo-api`."""

from __future__ import annotations


def run() -> None:
    import os

    import uvicorn

    port = int(os.environ.get("PORT", os.environ.get("TRENDALGO_API_PORT", "8000")))
    host = os.environ.get("TRENDALGO_API_HOST", "127.0.0.1")
    uvicorn.run("trendalgo.api.app:create_app", factory=True, host=host, port=port)


if __name__ == "__main__":
    run()
