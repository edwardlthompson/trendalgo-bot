#!/usr/bin/env python3
"""Run trendalgo unit tests (Windows-friendly)."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    try:
        import pytest  # noqa: F401
    except ImportError:
        subprocess.check_call(
            [
                sys.executable,
                "-m",
                "pip",
                "install",
                "-q",
                "pytest",
                "pytest-cov",
                "pydantic",
                "pandas",
            ]
        )
    return subprocess.call([sys.executable, "-m", "pytest", "-q", "tests"], cwd=ROOT)


if __name__ == "__main__":
    raise SystemExit(main())
