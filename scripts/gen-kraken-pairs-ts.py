"""Generate examples/web/src/data/krakenUsdPairs.ts from static_kraken_usd.py."""
from pathlib import Path

root = Path(__file__).resolve().parents[1]
src = root / "src" / "trendalgo" / "exchanges" / "static_kraken_usd.py"
out = root / "examples" / "web" / "src" / "data" / "krakenUsdPairs.ts"
ns: dict = {}
exec(src.read_text(encoding="utf-8"), ns)
pairs = ns["KRAKEN_USD_PAIRS"]
lines = ["export const KRAKEN_USD_PAIRS = ["]
for pair in pairs:
    lines.append(f'  "{pair}",')
lines.append("] as const;")
lines.append("")
lines.append("export function krakenPairsFallback(): string[] {")
lines.append("  return [...KRAKEN_USD_PAIRS];")
lines.append("}")
lines.append("")
out.write_text("\n".join(lines), encoding="utf-8")
print(f"wrote {len(pairs)} pairs to {out}")
