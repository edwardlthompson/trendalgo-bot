import type { AccountSummary } from "../portfolio/AccountsPanel";
import type { ExchangeIconMeta } from "./iconRegistry";

export type ExchangeSegment = {
  exchange: string;
  brand: string;
  color: string;
  total_usd: number;
  pct: number;
  widthPct: number;
};

export function sortAccountsByValue(accounts: AccountSummary[]): AccountSummary[] {
  return [...accounts].sort((a, b) => b.total_usd - a.total_usd);
}

export function buildExchangeSegments(
  accounts: AccountSummary[],
  totalUsd: number,
  registry: Map<string, ExchangeIconMeta>,
): ExchangeSegment[] {
  const sorted = sortAccountsByValue(accounts);
  const base = totalUsd > 0 ? totalUsd : sorted.reduce((sum, a) => sum + a.total_usd, 0);
  return sorted.map((acc) => {
    const meta = registry.get(acc.exchange);
    const pct = base > 0 ? acc.total_usd / base : 0;
    return {
      exchange: acc.exchange,
      brand: meta?.brand ?? acc.exchange,
      color: meta?.color ?? "#888888",
      total_usd: acc.total_usd,
      pct,
      widthPct: pct * 100,
    };
  });
}
