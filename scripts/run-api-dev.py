#!/usr/bin/env python3
"""Start TrendAlgo FastAPI dev server (editable src + optional uv venv)."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from trendalgo.api.main import run

if __name__ == "__main__":
    run()
