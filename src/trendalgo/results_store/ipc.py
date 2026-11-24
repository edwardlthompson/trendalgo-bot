"""Versioned IPC handshake between Avalonia shell and Python engine."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

PROTOCOL_VERSION = 1
HANDSHAKE_FILE = "engine_ipc.json"


@dataclass(frozen=True)
class IpcHandshake:
    protocol_version: int
    engine_version: str
    schema_version: int
    catalog_hash: str
    results_db: str
    pid: int | None = None

    def compatible_with_shell(self, shell_protocol: int, min_schema: int) -> bool:
        return self.protocol_version == shell_protocol and self.schema_version >= min_schema


def handshake_payload(
    *,
    engine_version: str,
    schema_version: int,
    catalog_hash: str,
    results_db: str,
    pid: int | None = None,
) -> IpcHandshake:
    return IpcHandshake(
        protocol_version=PROTOCOL_VERSION,
        engine_version=engine_version,
        schema_version=schema_version,
        catalog_hash=catalog_hash,
        results_db=results_db,
        pid=pid,
    )


def write_handshake(root: Path, handshake: IpcHandshake) -> Path:
    path = root / HANDSHAKE_FILE
    path.write_text(json.dumps(asdict(handshake), indent=2) + "\n", encoding="utf-8")
    return path


def read_handshake(root: Path) -> IpcHandshake | None:
    path = root / HANDSHAKE_FILE
    if not path.is_file():
        return None
    raw: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    return IpcHandshake(
        protocol_version=int(raw["protocol_version"]),
        engine_version=str(raw["engine_version"]),
        schema_version=int(raw["schema_version"]),
        catalog_hash=str(raw.get("catalog_hash", "")),
        results_db=str(raw["results_db"]),
        pid=int(raw["pid"]) if raw.get("pid") is not None else None,
    )
