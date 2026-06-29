import type { FleetResultRow } from "../api/client";

export function buyHoldFromSummary(
  summary: Record<string, unknown> | undefined,
): FleetResultRow | undefined {
  const row = summary?.buy_and_hold;
  if (!row || typeof row !== "object") return undefined;
  return row as FleetResultRow;
}

export function buyHoldNet(summary: Record<string, unknown> | undefined): number | null {
  const bh = buyHoldFromSummary(summary);
  if (bh?.net_profit == null || !Number.isFinite(Number(bh.net_profit))) return null;
  return Number(bh.net_profit);
}

export function beatsBuyHold(row: FleetResultRow, bhNet: number): boolean {
  return Number(row.net_profit) > bhNet;
}

export function hasPositivePl(row: FleetResultRow): boolean {
  return Number(row.net_profit) > 0;
}

export function filterBeatsBuyHold(rows: FleetResultRow[], bhNet: number | null): FleetResultRow[] {
  return rows.filter((row) => {
    if (!hasPositivePl(row)) return false;
    if (bhNet == null) return true;
    return beatsBuyHold(row, bhNet);
  });
}

export function vsBuyHoldAmount(netProfit: number, bhNet: number): number {
  return netProfit - bhNet;
}

export function netProfitPct(netProfit: number, stakeUsd: number): number {
  if (stakeUsd <= 0) return 0;
  return (netProfit / stakeUsd) * 100;
}

export function formatNetProfitPct(netProfit: number, stakeUsd: number): string {
  const pct = netProfitPct(netProfit, stakeUsd);
  const sign = pct > 0 ? "+" : "";
  return `${sign}${pct.toFixed(2)}%`;
}

export function formatVsBuyHoldPct(netProfit: number, bhNet: number, stakeUsd: number): string {
  const delta = netProfitPct(netProfit, stakeUsd) - netProfitPct(bhNet, stakeUsd);
  const sign = delta > 0 ? "+" : "";
  return `${sign}${delta.toFixed(2)}%`;
}

export function strategyOptimizedMarker(row: FleetResultRow): boolean {
  return Boolean(row.tsl_optimized || row.optimized);
}
