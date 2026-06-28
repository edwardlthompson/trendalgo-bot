import { describe, expect, it, vi } from "vitest";
import {
  buildLocalBotDetail,
  isPaperTrading,
  resolveBotDetail,
  syntheticBotChart,
} from "./botDetailLocal";

const ctx = {
  dashboard: {
    dry_run: true,
    equity_usd: 1000,
    open_trades: [],
    open_orders: [],
    bot_count: 1,
    strategy_id: "multi-tf-example",
    pair: "BTC/USD",
    risk: {},
    bots: [
      {
        id: 1,
        label: "Bot-1",
        strategy_id: "multi-tf-example",
        pair: "BTC/USD",
        enabled: true,
        equity_usd: 1000,
        timeframe: "1h",
        realized_pnl_usd: 10,
        unrealized_pnl_usd: 5,
        pnl_usd: 15,
        pnl_pct: 0.015,
        trade_count: 2,
      },
    ],
  },
  strategyParams: { rsi_entry: 35, rsi_exit: 65 },
  taLibrary: [
    {
      name: "Momentum Indicators",
      items: [{ id: "RSI", name: "RSI", category: "Momentum Indicators" }],
    },
  ],
};

describe("botDetailLocal", () => {
  it("builds chart and detail from dashboard cache", () => {
    const chart = syntheticBotChart("BTC/USD");
    expect(chart.length).toBeGreaterThan(20);
    const detail = buildLocalBotDetail(1, ctx);
    expect(detail.bot.label).toBe("Bot-1");
    expect(detail.realized_pnl_usd).toBe(10);
    expect(detail.unrealized_pnl_usd).toBe(5);
    expect(detail.chart.length).toBeGreaterThan(0);
    expect(detail.available_timeframes).toContain("60");
    expect(detail.backtest_top5?.length).toBeGreaterThan(0);
    expect(detail.simulated_trades?.length).toBeGreaterThan(0);
  });

  it("uses local detail in paper mode without calling API", async () => {
    const fetchRemote = vi.fn(() => Promise.reject(new Error("offline")));
    const resolved = await resolveBotDetail(1, ctx, fetchRemote);
    expect(resolved.local).toBe(true);
    expect(resolved.detail.trades.length).toBe(2);
    expect(fetchRemote).not.toHaveBeenCalled();
  });

  it("falls back locally when live API fails", async () => {
    const liveCtx = { ...ctx, dashboard: { ...ctx.dashboard!, dry_run: false } };
    expect(isPaperTrading(liveCtx)).toBe(false);
    const resolved = await resolveBotDetail(1, liveCtx, () => Promise.reject(new Error("500")));
    expect(resolved.local).toBe(true);
    expect(resolved.detail.bot.id).toBe(1);
  });
});
