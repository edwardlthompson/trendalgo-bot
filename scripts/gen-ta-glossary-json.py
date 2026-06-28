#!/usr/bin/env python3
"""Export TA glossary JSON for frontend offline fallback."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from trendalgo.ta.glossary import build_ta_glossary  # noqa: E402

OUT = ROOT / "examples" / "web" / "public" / "data" / "ta-glossary.json"


def main() -> None:
    entries = build_ta_glossary()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(
        json.dumps({"entries": entries, "count": len(entries)}, indent=2), encoding="utf-8"
    )
    print(f"wrote {len(entries)} entries to {OUT}")


if __name__ == "__main__":
    main()
