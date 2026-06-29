#!/usr/bin/env python3
"""Generate examples/web/src/data/*.ts fallbacks from Python TA catalogs."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from trendalgo.exchanges.static_kraken_usd import KRAKEN_USD_PAIRS  # noqa: E402
from trendalgo.ta.categories import CATEGORY_ORDER, build_ta_library  # noqa: E402
from trendalgo.ta.glossary import build_ta_glossary  # noqa: E402

OUT_DIR = ROOT / "examples" / "web" / "src" / "data"


def write_kraken_pairs() -> None:
    lines = ["export const KRAKEN_USD_PAIRS = ["]
    for pair in KRAKEN_USD_PAIRS:
        lines.append(f'  "{pair}",')
    lines.extend(
        [
            "] as const;",
            "",
            "export function krakenPairsFallback(): string[] {",
            "  return [...KRAKEN_USD_PAIRS];",
            "}",
            "",
        ]
    )
    path = OUT_DIR / "krakenUsdPairs.ts"
    path.write_text("\n".join(lines), encoding="utf-8")
    print(f"wrote {len(KRAKEN_USD_PAIRS)} pairs -> {path}")


def write_ta_glossary() -> None:
    entries = build_ta_glossary()
    blob = json.dumps(entries, ensure_ascii=False)
    content = f"""import type {{ TaGlossaryEntry }} from "./taGlossaryTypes";

const BUNDLED_ENTRIES: TaGlossaryEntry[] = {blob};

let entries: TaGlossaryEntry[] = BUNDLED_ENTRIES;

export type {{ TaGlossaryEntry }} from "./taGlossaryTypes";

export function setTaGlossaryEntries(next: TaGlossaryEntry[]): void {{
  entries = next;
}}

export async function ensureTaGlossaryLoaded(): Promise<void> {{
  if (entries.length > 0) return;
  try {{
    const res = await fetch("/data/ta-glossary.json");
    if (!res.ok) return;
    const data = (await res.json()) as {{ entries?: TaGlossaryEntry[] }};
    if (data.entries?.length) entries = data.entries;
  }} catch {{
    /* offline fallback uses bundled entries */
  }}
}}

export function allTaGlossaryEntries(): TaGlossaryEntry[] {{
  return entries;
}}

export function taGlossaryEntry(id: string): TaGlossaryEntry {{
  const key = id.toUpperCase();
  const hit = entries.find((e) => e.id === key);
  if (!hit) {{
    return {{ id: key, title: key, short: key, long: key, formula: "", category: "Other" }};
  }}
  return hit;
}}

export function glossaryCategoriesWithCounts(): Array<{{ category: string; count: number }}> {{
  const counts = new Map<string, number>();
  for (const entry of entries) {{
    const cat = entry.category ?? "Other";
    counts.set(cat, (counts.get(cat) ?? 0) + 1);
  }}
  return [...counts.entries()]
    .map(([category, count]) => ({{ category, count }}))
    .sort((a, b) => a.category.localeCompare(b.category));
}}
"""
    types = """export type TaGlossaryEntry = {
  id: string;
  title: string;
  short: string;
  long: string;
  formula: string;
  category?: string;
  related?: string[];
};
"""
    (OUT_DIR / "taGlossaryTypes.ts").write_text(types, encoding="utf-8")
    path = OUT_DIR / "taGlossary.ts"
    path.write_text(content, encoding="utf-8")
    print(f"wrote {len(entries)} glossary entries -> {path}")


def write_exchange_fees_fallback() -> None:
    path_json = ROOT / "config" / "exchange_fees.json"
    data = json.loads(path_json.read_text(encoding="utf-8"))
    tier = data.get("tier", "retail_default")
    schedules = []
    for exchange_id, row in sorted((data.get("exchanges") or {}).items()):
        schedules.append(
            {
                "exchange_id": exchange_id,
                "taker_pct": row["taker_pct"],
                "maker_pct": row["maker_pct"],
                "tier": tier,
                "source_url": row.get("source_url", ""),
            }
        )
    blob = json.dumps(schedules, ensure_ascii=False)
    content = f"""import type {{ ExchangeFeeSchedule }} from "../api/client";

const BUNDLED_EXCHANGE_FEES: ExchangeFeeSchedule[] = {blob};

export function bundledExchangeFees(): ExchangeFeeSchedule[] {{
  return BUNDLED_EXCHANGE_FEES;
}}

export function mergeFeeCatalogs(
  api: ExchangeFeeSchedule[],
  existing: ExchangeFeeSchedule[] = [],
): ExchangeFeeSchedule[] {{
  const map = new Map(bundledExchangeFees().map((e) => [e.exchange_id, e]));
  for (const row of existing) map.set(row.exchange_id, row);
  for (const row of api) map.set(row.exchange_id, row);
  return [...map.values()].sort((a, b) => a.exchange_id.localeCompare(b.exchange_id));
}}

export function feeForExchange(
  exchangeId: string,
  catalog: ExchangeFeeSchedule[],
): ExchangeFeeSchedule | null {{
  return (
    catalog.find((e) => e.exchange_id === exchangeId) ??
    bundledExchangeFees().find((e) => e.exchange_id === exchangeId) ??
    null
  );
}}
"""
    path = OUT_DIR / "exchangeFeesFallback.ts"
    path.write_text(content, encoding="utf-8")
    print(f"wrote {len(schedules)} exchange fees -> {path}")


def write_ta_library_fallback() -> None:
    items = build_ta_library()
    names = sorted({item["name"] for item in items})
    by_category: dict[str, list[dict[str, str]]] = {cat: [] for cat in CATEGORY_ORDER}
    for item in items:
        by_category.setdefault(item["category"], []).append(item)
    categories = [
        {"name": cat, "items": sorted(by_category.get(cat, []), key=lambda x: x["name"])}
        for cat in CATEGORY_ORDER
        if by_category.get(cat)
    ]
    blob = json.dumps(categories, ensure_ascii=False)
    names_blob = json.dumps(names, ensure_ascii=False)
    content = f"""import type {{ TaLibraryCategory }} from "../api/client";

export const TA_FUNCTION_NAMES: string[] = {names_blob};

const BUNDLED_LIBRARY: TaLibraryCategory[] = {blob};

export function buildFallbackTaLibrary(): TaLibraryCategory[] {{
  return BUNDLED_LIBRARY;
}}

export async function ensureTaLibraryBundled(): Promise<void> {{
  /* bundled library is always available */
}}
"""
    path = OUT_DIR / "taLibraryFallback.ts"
    path.write_text(content, encoding="utf-8")
    print(f"wrote {len(items)} strategies -> {path}")


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    write_kraken_pairs()
    write_ta_glossary()
    write_ta_library_fallback()
    write_exchange_fees_fallback()
    print("gen-web-data-ts: done")


if __name__ == "__main__":
    main()
