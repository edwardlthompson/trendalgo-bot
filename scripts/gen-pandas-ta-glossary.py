#!/usr/bin/env python3
"""Generate pandas-ta-classic glossary entries from library docstrings."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

OUT = ROOT / "src" / "trendalgo" / "ta" / "pandas_ta_glossary_data.py"

TALIB_UPPER = set()  # filled from catalog at runtime


def _load_talib() -> set[str]:
    from trendalgo.ta.catalog import TA_FUNCTION_NAMES

    return {n.upper() for n in TA_FUNCTION_NAMES}


def _slug_to_id(slug: str) -> str:
    return slug.upper()


def _clean(text: str) -> str:
    text = re.sub(r"\s+", " ", text.strip())
    return text[:500]


def _extract_short(doc: str | None, title: str) -> str:
    if not doc:
        return f"{title} technical indicator computed from OHLCV bars."
    lines = [ln.strip() for ln in doc.strip().splitlines() if ln.strip()]
    for line in lines[1:6]:
        if line.startswith(("Sources:", "Calculation:", "Default Inputs:", "Args:")):
            continue
        if len(line) > 20:
            return _clean(line)
    return f"{title} technical indicator computed from OHLCV bars."


def _extract_formula(doc: str | None, slug: str) -> str:
    if not doc:
        return f"{slug.upper()}(open, high, low, close, volume)"
    calc = re.search(r"Calculation:\s*(.+?)(?:\nArgs:|\nKwargs:|\Z)", doc, re.S | re.I)
    if calc:
        body = calc.group(1).strip()
        lines = [
            ln.strip()
            for ln in body.splitlines()
            if ln.strip() and not ln.strip().startswith("Sources:")
        ]
        # Drop header-only lines, keep equations.
        eq = [
            ln
            for ln in lines
            if ln.lower().startswith(
                (
                    "default inputs",
                    "typical",
                    "vfi",
                    "inter",
                    "cutoff",
                    "mf",
                    "vave",
                    "vmax",
                    "vc",
                    "vcp",
                    "bb ",
                    "kc ",
                    "mom",
                    "hma",
                    "wma",
                    "upper",
                    "lower",
                    "middle",
                    "macd",
                    "signal",
                    "rsi",
                    "ema",
                    "sma",
                    "atr",
                    "adx",
                    "supert",
                    "length",
                    "close",
                    "high",
                    "low",
                    "open",
                    "volume",
                )
            )
            or "=" in ln
        ]
        if eq:
            return _clean(" ".join(eq[:8]))
        return _clean(" ".join(lines[:6]))
    inputs = re.search(r"Default Inputs:\s*(.+?)(?:\n|$)", doc, re.I)
    if inputs:
        return _clean(f"Default inputs: {inputs.group(1).strip()}")
    lines = [ln.strip() for ln in doc.splitlines() if ln.strip()]
    if len(lines) > 1:
        return _clean(lines[1])
    return f"{slug.upper()}(open, high, low, close, volume)"


def _extract_long(doc: str | None, title: str, short: str) -> str:
    if not doc:
        return (
            f"{title} is evaluated on each OHLCV bar using open, high, low, close, and volume. "
            f"{short} Backtests derive entries and exits from the indicator output series."
        )
    paras: list[str] = []
    for line in doc.splitlines():
        line = line.strip()
        if not line or line.startswith(("Calculation:", "Default Inputs:", "Args:", "Sources:")):
            continue
        if line == title or line.lower() == title.lower():
            continue
        paras.append(line)
        if len(paras) >= 3:
            break
    body = " ".join(paras) if paras else short
    return _clean(
        f"{body} The indicator uses standard OHLCV inputs and integrates with the unified TA backtest engine."
    )


def main() -> None:
    import pandas as pd
    import pandas_ta_classic as pta

    talib = _load_talib()
    frame = pd.DataFrame(
        {
            "open": [1.0, 2.0, 3.0, 4.0, 5.0] * 30,
            "high": [2.0, 3.0, 4.0, 5.0, 6.0] * 30,
            "low": [0.5, 1.5, 2.5, 3.5, 4.5] * 30,
            "close": [1.5, 2.5, 3.5, 4.5, 5.5] * 30,
            "volume": [100.0] * 150,
        }
    )
    slugs = frame.ta.indicators(as_list=True)
    entries: dict[str, dict[str, str]] = {}
    for slug in slugs:
        upper = _slug_to_id(slug)
        if upper in talib or slug.startswith("cdl_"):
            continue
        fn = getattr(pta, slug, None)
        doc = fn.__doc__ if fn else None
        title = upper.replace("_", " ").title()
        short = _extract_short(doc, title)
        formula = _extract_formula(doc, slug)
        long = _extract_long(doc, title, short)
        entries[upper] = {
            "title": title,
            "short": short,
            "long": long,
            "formula": formula,
        }

    lines = [
        '"""Auto-generated glossary for extended TA indicators (pandas-ta-classic)."""',
        "",
        "from __future__ import annotations",
        "",
        "PANDAS_TA_GLOSSARY_ENTRIES: dict[str, dict[str, str]] = {",
    ]
    for key in sorted(entries):
        row = entries[key]
        lines.append(f'    "{key}": {{')
        for field in ("title", "short", "long", "formula"):
            val = row[field].replace("\\", "\\\\").replace('"', '\\"')
            lines.append(f'        "{field}": "{val}",')
        lines.append("    },")
    lines.append("}")
    lines.append("")
    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"wrote {len(entries)} entries to {OUT}")

    audit = OUT.with_suffix(".audit.json")
    placeholders = [k for k, v in entries.items() if "documentation" in v["formula"].lower()]
    audit.write_text(
        json.dumps({"count": len(entries), "placeholder_formulas": placeholders}, indent=2),
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
