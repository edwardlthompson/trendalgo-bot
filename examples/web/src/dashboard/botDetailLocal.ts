import type { BotDetailData, DashboardData, TaLibraryCategory } from "../api/client";
import { buildTradeRegions } from "../charts/tradeRegions";
import { TRADINGVIEW_INTERVALS, TRADINGVIEW_INTERVAL_LABELS, normalizeTimeframe } from "../components/tradingViewIntervals";
import { mergeBotWithPersisted, loadBotSettings } from "../settings/settingsStore";

export type BotDetailContext = {
  dashboard: DashboardData | null;
  strategyParams: Record<string, number>;
  taLibrary: TaLibraryCategory[];
};

export type ResolvedBotDetail = {
  detail: BotDetailData;
  local: boolean;
};

type BotRecord = NonNullable<DashboardData["bots"]>[number];

function basePriceForPair(pair: string): number {
  const base = pair.split("/")[0]?.toUpperCase() ?? "BTC";
  if (base === "BTC") return 98_000;
  if (base === "ETH") return 3_200;
  return 100;
}

export function syntheticBotOhlcv(pair: string, days = 30): BotDetailData["ohlcv"] {
  const line = syntheticBotChart(pair, days);
  return line.map((p) => {
    const w = p.value * 0.002;
    return {
      time: p.time,
      open: p.value - w * 0.3,
      high: p.value + w,
      low: p.value - w,
      close: p.value,
      volume: 1000,
    };
  });
}

export function syntheticBotChart(pair: string, days = 30): Array<{ time: number; value: number }> {
  const points: Array<{ time: number; value: number }> = [];
  const now = Math.floor(Date.now() / 1000);
  const start = basePriceForPair(pair);
  for (let i = days; i >= 0; i -= 1) {
    const t = now - i * 86_400;
    const wave = Math.sin(i / 5) * (start * 0.012);
    const drift = (days - i) * (start * 0.0004);
    points.push({ time: t, value: Math.round((start + drift + wave) * 100) / 100 });
  }
  return points;
}

function samplePaperTrades(bot: BotRecord): BotDetailData["trades"] {
  const now = Date.now();
  return [
    {
      pair: bot.pair,
      side: "buy",
      stake_usd: Math.round(bot.equity_usd * 0.1),
      pnl_usd: 0,
      created_at: new Date(now - 5 * 86_400_000).toISOString(),
    },
    {
      pair: bot.pair,
      side: "sell",
      stake_usd: Math.round(bot.equity_usd * 0.08),
      pnl_usd: Number(bot.realized_pnl_usd ?? 12),
      created_at: new Date(now - 2 * 86_400_000).toISOString(),
    },
  ];
}

function mockSimTrades(bot: BotRecord, chart: Array<{ time: number; value: number }>): BotDetailData["simulated_trades"] {
  if (chart.length < 8) return [];
  let buyIdx = 2;
  for (let i = 2; i < chart.length - 2; i += 1) {
    const prev = chart[i - 1]?.value ?? 0;
    const cur = chart[i]?.value ?? 0;
    const next = chart[i + 1]?.value ?? 0;
    if (cur <= prev && cur <= next) {
      buyIdx = i;
      break;
    }
  }
  let sellIdx = Math.min(buyIdx + 4, chart.length - 2);
  for (let i = buyIdx + 2; i < chart.length - 1; i += 1) {
    const prev = chart[i - 1]?.value ?? 0;
    const cur = chart[i]?.value ?? 0;
    const next = chart[i + 1]?.value ?? 0;
    if (cur >= prev && cur >= next) {
      sellIdx = i;
      break;
    }
  }
  if (sellIdx <= buyIdx) sellIdx = Math.min(buyIdx + 3, chart.length - 1);
  const stake = bot.equity_usd * 0.1;
  const entry = chart[buyIdx]?.value ?? chart[0].value;
  const exit = chart[sellIdx]?.value ?? entry;
  const pnl = stake * (exit / entry - 1);
  return [
    {
      pair: bot.pair,
      side: "buy",
      stake_usd: stake,
      pnl_usd: 0,
      created_at: new Date(chart[buyIdx].time * 1000).toISOString(),
      simulated: true,
    },
    {
      pair: bot.pair,
      side: "sell",
      stake_usd: stake,
      pnl_usd: Math.round(pnl * 100) / 100,
      created_at: new Date(chart[sellIdx].time * 1000).toISOString(),
      simulated: true,
    },
  ];
}

function mockTop5(ctx: BotDetailContext, bot: BotRecord): BotDetailData["backtest_top5"] {
  const ids = ctx.taLibrary.flatMap((c) => c.items.map((i) => i.id)).slice(0, 5);
  if (!ids.length) {
    return [
      { id: "RSI", fn: "RSI", profit_total: 24.5, timeframe: "60" },
      { id: "MACD", fn: "MACD", profit_total: 18.2, timeframe: "60" },
    ];
  }
  return ids.map((id, idx) => ({
    id,
    fn: id,
    profit_total: 30 - idx * 4,
    timeframe: normalizeTimeframe(String(bot.timeframe ?? "60")),
    pair: bot.pair,
  }));
}

export function enrichDetailWithPersisted(detail: BotDetailData): BotDetailData {
  const bot = mergeBotWithPersisted(detail.bot.id, detail.bot) as BotRecord;
  const saved = loadBotSettings(detail.bot.id);
  return {
    ...detail,
    bot: {
      ...bot,
      timeframe: normalizeTimeframe(String(bot.timeframe ?? saved?.timeframe ?? "60")),
    },
    strategy_params: saved?.ta_params
      ? { ...detail.strategy_params, ...saved.ta_params }
      : detail.strategy_params,
  };
}

export function buildLocalBotDetail(botId: number, ctx: BotDetailContext): BotDetailData {
  const raw = ctx.dashboard?.bots?.find((row) => row.id === botId);
  if (!raw) {
    throw new Error(`bot ${botId} not found in dashboard cache`);
  }
  const bot = mergeBotWithPersisted(botId, raw) as BotRecord;
  const realized = Number(bot.realized_pnl_usd ?? 0);
  const unrealized = Number(bot.unrealized_pnl_usd ?? 0);
  const total = Number(bot.pnl_usd ?? realized + unrealized);
  const equity = Number(bot.equity_usd);
  const trades = (bot.trade_count ?? 0) > 0 ? samplePaperTrades(bot) : [];
  const chart = syntheticBotChart(bot.pair);
  const ohlcv = syntheticBotOhlcv(bot.pair);
  const simTrades = mockSimTrades(bot, chart);
  const paramSpecs = [{ key: "timeperiod", label: "Period", default: 14 }];
  const base = bot.pair.split("/")[0]?.toUpperCase() ?? "BTC";
  const quote = bot.pair.split("/")[1]?.toUpperCase() ?? "USD";
  const tradeMarkers = (() => {
    let stake = 0;
    return trades.map((t) => {
      const time = Math.floor(new Date(t.created_at).getTime() / 1000);
      if (t.side === "buy") {
        stake = Number(t.stake_usd) || stake;
        return { time, side: t.side };
      }
      const pnl = Number(t.pnl_usd);
      const pnlPct = stake > 0 ? (pnl / stake) * 100 : undefined;
      return { time, side: t.side, pnl_usd: pnl, pnl_pct: pnlPct };
    });
  })();
  const simMarkers = (() => {
    let stake = 0;
    return (simTrades ?? []).map((t) => {
      const time = Math.floor(new Date(t.created_at).getTime() / 1000);
      if (t.side === "buy") {
        stake = Number(t.stake_usd) || stake;
        return { time, side: t.side };
      }
      const pnl = Number(t.pnl_usd);
      const pnlPct = stake > 0 ? (pnl / stake) * 100 : undefined;
      return { time, side: t.side, pnl_usd: pnl, pnl_pct: pnlPct };
    });
  })();

  return enrichDetailWithPersisted({
    bot: {
      ...bot,
      exchange: bot.exchange ?? "kraken",
      equity_mode: (bot as BotRecord & { equity_mode?: string }).equity_mode ?? "quote",
      equity_input: Number((bot as BotRecord & { equity_input?: number }).equity_input ?? bot.equity_usd),
      timeframe: normalizeTimeframe(String(bot.timeframe ?? "60")),
    },
    realized_pnl_usd: realized,
    unrealized_pnl_usd: unrealized,
    pnl_usd: total,
    pnl_pct: equity > 0 ? total / equity : 0,
    trade_count: Number(bot.trade_count ?? trades.length),
    trades,
    simulated_trades: simTrades,
    chart,
    ohlcv,
    trade_markers: tradeMarkers,
    simulated_markers: simMarkers,
    trade_regions: buildTradeRegions(tradeMarkers, ohlcv ?? []),
    simulated_regions: buildTradeRegions(simMarkers, ohlcv ?? []),
    equity_limits: {
      base: { symbol: base, max: 10 },
      quote: { symbol: quote, max: 50_000 },
      portfolio_usd: 100_000,
      paper: true,
    },
    strategy_params: { timeperiod: 14, ...ctx.strategyParams },
    available_timeframes: [...TRADINGVIEW_INTERVALS],
    timeframe_labels: TRADINGVIEW_INTERVAL_LABELS,
    param_specs: paramSpecs,
    backtest_top5: mockTop5(ctx, bot),
  });
}

export function isPaperTrading(ctx: BotDetailContext): boolean {
  return ctx.dashboard?.dry_run !== false;
}

export async function resolveBotDetail(
  botId: number,
  ctx: BotDetailContext,
  fetchRemote: (id: number) => Promise<BotDetailData>,
): Promise<ResolvedBotDetail> {
  if (isPaperTrading(ctx)) {
    return { detail: buildLocalBotDetail(botId, ctx), local: true };
  }
  try {
    const detail = enrichDetailWithPersisted(await fetchRemote(botId));
    return { detail, local: false };
  } catch {
    return { detail: buildLocalBotDetail(botId, ctx), local: true };
  }
}
