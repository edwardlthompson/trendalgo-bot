#!/usr/bin/env python3
"""Export TA library categories JSON for frontend offline fallback."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from trendalgo.ta.categories import CATEGORY_ORDER, build_ta_library  # noqa: E402

OUT = ROOT / "examples" / "web" / "public" / "data" / "ta-library.json"


def main() -> None:
    items = build_ta_library()
    by_category: dict[str, list[dict[str, str]]] = {cat: [] for cat in CATEGORY_ORDER}
    for item in items:
        by_category.setdefault(item["category"], []).append(item)
    categories = [
        {"name": cat, "items": sorted(by_category.get(cat, []), key=lambda x: x["name"])}
        for cat in CATEGORY_ORDER
        if by_category.get(cat)
    ]
    payload = {"categories": categories, "count": len(items)}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"wrote {len(items)} strategies to {OUT}")


if __name__ == "__main__":
    main()
