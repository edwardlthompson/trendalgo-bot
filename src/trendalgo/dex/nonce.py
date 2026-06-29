"""EVM nonce tracking for live swaps (S24)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, cast


class NonceStore:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.is_file():
            self.path.write_text("{}", encoding="utf-8")

    def _load(self) -> dict[str, int]:
        raw = json.loads(self.path.read_text(encoding="utf-8"))
        return cast(dict[str, int], raw)

    def _save(self, data: dict[str, int]) -> None:
        self.path.write_text(json.dumps(data, indent=0), encoding="utf-8")

    def next_nonce(self, venue_id: str) -> int:
        data = self._load()
        nonce = int(data.get(venue_id, 0))
        data[venue_id] = nonce + 1
        self._save(data)
        return nonce

    def status(self) -> dict[str, Any]:
        return {"nonces": self._load()}
