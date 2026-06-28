import type { BotTradeMarker, OhlcvCandle, TradeHighlightRegion } from "./BotChart";

export function buildTradeRegions(
  markers: BotTradeMarker[],
  candles: OhlcvCandle[],
): TradeHighlightRegion[] {
  if (!markers.length || !candles.length) return [];
  const byTime = new Map(candles.map((c) => [c.time, c.close]));
  const times = candles.map((c) => c.time).sort((a, b) => a - b);
  const closeAt = (ts: number): number => {
    if (byTime.has(ts)) return byTime.get(ts)!;
    const prior = times.filter((t) => t <= ts);
    return byTime.get(prior[prior.length - 1] ?? times[0]!) ?? 0;
  };
  const ordered = [...markers].sort((a, b) => a.time - b.time);
  const regions: TradeHighlightRegion[] = [];
  let openBuy: BotTradeMarker | null = null;
  for (const mark of ordered) {
    const side = mark.side.toLowerCase();
    if (side === "buy") {
      openBuy = mark;
      continue;
    }
    if (side !== "sell" || !openBuy) continue;
    const entryTs = openBuy.time;
    const entryPx = closeAt(entryTs);
    const exitPx = closeAt(mark.time);
    const pnl = mark.pnl_usd;
    regions.push({
      time_start: entryTs,
      time_end: mark.time,
      entry_price: entryPx,
      exit_price: exitPx,
      pnl_usd: pnl ?? null,
      profitable: pnl != null ? pnl >= 0 : exitPx >= entryPx,
    });
    openBuy = null;
  }
  return regions;
}
