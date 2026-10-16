"""Installer checks (W-OCI4, row 15). The image archive must match a pinned SHA-256 before it loads.

    python -m trendalgo.botd.installer --manifest docker/botd-release.json --image <archive>

Exit 0 when the archive matches the pin, 1 when it is refused. Sizing warnings never block.
"""

from __future__ import annotations

import argparse
import hashlib
import hmac
import json
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path

MAX_OCPU = 2
MAX_MEM_GB = 12
MEMINFO = Path("/proc/meminfo")
_SHA256 = re.compile(r"[0-9a-f]{64}")


class InstallRefused(RuntimeError):
    """The image cannot be installed: no valid pin, or the archive does not match the pin."""


@dataclass(frozen=True)
class ReleasePin:
    version: str
    image_sha256: str | None


def load_pin(manifest: Path) -> ReleasePin:
    data = json.loads(manifest.read_text(encoding="utf-8"))
    raw = data.get("image_sha256")
    pin = raw.lower() if isinstance(raw, str) else ""
    return ReleasePin(
        version=str(data.get("version", "")),
        image_sha256=pin if _SHA256.fullmatch(pin) else None,
    )


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify_image(pin: ReleasePin, image: Path) -> None:
    if pin.image_sha256 is None:
        raise InstallRefused("the release manifest has no pinned SHA-256; pin it before installing")
    if not hmac.compare_digest(sha256_file(image), pin.image_sha256):
        raise InstallRefused(f"{image.name} does not match the pinned SHA-256")


def sizing_warnings(cpus: int, mem_gb: float | None) -> list[str]:
    warnings: list[str] = []
    if cpus > MAX_OCPU:
        warnings.append(f"host reports {cpus} CPUs; Always Free A1 allows {MAX_OCPU} OCPU in total")
    if mem_gb is None:
        warnings.append(
            f"host memory not detected; check the {MAX_MEM_GB} GB Always Free limit by hand"
        )
    elif mem_gb > MAX_MEM_GB:
        warnings.append(
            f"host reports {mem_gb:.1f} GB memory; Always Free A1 allows {MAX_MEM_GB} GB in total"
        )
    return warnings


def detect_mem_gb(meminfo: Path = MEMINFO) -> float | None:
    """Total memory in GB from Linux meminfo (the host is Linux). None when it cannot be read."""
    try:
        text = meminfo.read_text(encoding="ascii", errors="replace")
    except OSError:
        return None
    for line in text.splitlines():
        if line.startswith("MemTotal:"):
            try:
                return int(line.split()[1]) / (1024 * 1024)
            except (IndexError, ValueError):
                return None
    return None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Verify the host image against its pinned SHA-256."
    )
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--image", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        verify_image(load_pin(args.manifest), args.image)
    except (InstallRefused, OSError, ValueError) as exc:
        print(f"install refused: {exc}", file=sys.stderr)
        return 1
    for line in sizing_warnings(os.cpu_count() or 0, detect_mem_gb()):
        print(f"warning: {line}")
    print("image verified against the pinned SHA-256")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
