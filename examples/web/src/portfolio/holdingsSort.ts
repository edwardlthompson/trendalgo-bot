export type HoldingsSortKey = "value" | "unrealized";
export type SortDirection = "asc" | "desc";

export const DUST_THRESHOLD_USD = 10;

function holdingMetric(
  holding: Record<string, number | string>,
  key: HoldingsSortKey,
): number {
  if (key === "value") return Number(holding.value_usd ?? 0);
  return Number(holding.unrealized_pnl_usd ?? 0);
}

export function sortHoldings(
  holdings: Array<Record<string, number | string>>,
  key: HoldingsSortKey,
  direction: SortDirection = "desc",
): Array<Record<string, number | string>> {
  const mult = direction === "desc" ? -1 : 1;
  return [...holdings].sort((a, b) => {
    const av = holdingMetric(a, key);
    const bv = holdingMetric(b, key);
    if (av !== bv) return (av - bv) * mult;
    return String(a.asset).localeCompare(String(b.asset));
  });
}

export function filterHoldings(
  holdings: Array<Record<string, number | string>>,
  options: { hideDust?: boolean },
): Array<Record<string, number | string>> {
  if (!options.hideDust) return holdings;
  return holdings.filter((h) => Number(h.value_usd ?? 0) >= DUST_THRESHOLD_USD);
}
