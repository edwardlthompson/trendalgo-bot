import type { Page, Route } from "@playwright/test";
import { buildFallbackTaLibrary } from "../src/data/taLibraryFallback";
import { krakenPairsFallback } from "../src/data/krakenUsdPairs";

const sampleDashboard = {
  dry_run: true,
  equity_usd: 1000,
  open_trades: [],
  open_orders: [],
  bot_count: 1,
  strategy_id: "multi-tf-example",
  pair: "BTC/USD",
  bots: [
    { id: 1, label: "Bot-1", strategy_id: "multi-tf-example", pair: "BTC/USD", enabled: true, equity_usd: 1000, engine: "native", exchange: "kraken", timeframe: "1h", realized_pnl_usd: 42.5, unrealized_pnl_usd: 5, pnl_usd: 47.5, pnl_pct: 0.0475, trade_count: 2 },
    { id: 2, label: "Bot-2", strategy_id: "grid-trading", pair: "ETH/USD", enabled: false, equity_usd: 500, engine: "native", exchange: "kraken", timeframe: "5m", realized_pnl_usd: -12, unrealized_pnl_usd: 0, pnl_usd: -12, pnl_pct: -0.024, trade_count: 1 },
  ],
  risk: {
    wallet_usd: 1000,
    equity_usd: 1000,
    daily_pnl_usd: 0,
    drawdown_pct: 0,
    open_exposure_usd: 0,
    circuit_breaker_active: false,
    paused: false,
    can_trade: true,
    block_reason: "ok",
  },
};

function mockEquityCurve(count: number, startValue = 42_000): Array<{ time: number; value: number }> {
  const points: Array<{ time: number; value: number }> = [];
  const now = Math.floor(Date.now() / 1000);
  for (let i = count; i >= 0; i -= 1) {
    const t = now - i * 86_400;
    const value = startValue + (count - i) * 150 + Math.sin(i / 7) * 800;
    points.push({ time: t, value: Math.round(value) });
  }
  return points;
}

const mockEquity1y = mockEquityCurve(365, 42_000);

function json(body: unknown): { status: number; contentType: string; body: string } {
  return {
    status: 200,
    contentType: "application/json",
    body: JSON.stringify(body),
  };
}

export async function mockTrendAlgoApi(page: Page, paused = false): Promise<void> {
  const risk = { ...sampleDashboard.risk, paused, can_trade: !paused };
  let mockBots = sampleDashboard.bots!.map((b) => ({ ...b }));
  let fleetStatus: "idle" | "running" | "complete" = "idle";
  let fleetPolls = 0;
  const dashboardPayload = () => ({
    ...sampleDashboard,
    risk,
    bots: mockBots,
    bot_count: mockBots.filter((b) => b.enabled).length,
  });

  await page.route(/\/api\/v1\//, async (route: Route) => {
    const url = route.request().url();
    const method = route.request().method();

    if (url.includes("/ws/live")) {
      await route.abort();
      return;
    }
    if (url.includes("/dashboard")) {
      await route.fulfill(json(dashboardPayload()));
      return;
    }
    if (url.includes("/risk/pause") && method === "POST") {
      risk.paused = true;
      risk.can_trade = false;
      await route.fulfill(json({ ok: true, paused: true }));
      return;
    }
    if (url.includes("/risk/resume") && method === "POST") {
      risk.paused = false;
      risk.can_trade = true;
      await route.fulfill(json({ ok: true, paused: false }));
      return;
    }
    if (url.includes("/risk")) {
      await route.fulfill(json(risk));
      return;
    }
    if (url.includes("/pairs") && !url.includes("/exchanges/")) {
      await route.fulfill(json({ pairs: krakenPairsFallback() }));
      return;
    }
    if (url.includes("/research/ta-glossary")) {
      await route.fulfill(
        json({
          entries: [
            {
              id: "RSI",
              title: "Relative Strength Index",
              short: "Momentum oscillator 0–100.",
              long: "Compares average gains vs losses.",
              formula: "RSI = 100 − (100 / (1 + RS))",
            },
          ],
          count: 1,
        }),
      );
      return;
    }
    if (url.includes("/research/ta-library")) {
      const categories = buildFallbackTaLibrary();
      await route.fulfill(json({ categories, count: categories.flatMap((c) => c.items).length }));
      return;
    }
    if (url.includes("/constants/timeframes")) {
      await route.fulfill(
        json({
          intervals: ["1", "60", "1D", "1W"],
          labels: { "1": "1 minute", "60": "1 hour", "1D": "1 day", "1W": "1 week" },
        }),
      );
      return;
    }
    if (url.match(/\/exchanges\/[^/]+\/pairs/)) {
      await route.fulfill(json({ exchange_id: "kraken", pairs: krakenPairsFallback() }));
      return;
    }
    if (url.includes("/strategies/multi-tf-example/params")) {
      if (method === "PUT") {
        await route.fulfill(
          json({
            strategy_id: "multi-tf-example",
            params: { rsi_entry: 30, rsi_exit: 65, lts_uniform_min: 0.55, stoploss: -0.05 },
          }),
        );
        return;
      }
      await route.fulfill(
        json({
          strategy_id: "multi-tf-example",
          params: { rsi_entry: 35, rsi_exit: 65, lts_uniform_min: 0.55, stoploss: -0.05 },
        }),
      );
      return;
    }
    if (url.includes("/backtest/latest")) {
      await route.fulfill(json({ result: null, metrics: null, equity_curve: [] }));
      return;
    }
    if (url.includes("/backtest/fleet/history/")) {
      await route.fulfill(
        json({
          rankings: [{ strategy_id: "RSI", timeframe: "60", net_profit: 100, trades: 5, rank: 1 }],
          total_rankings: 1,
          summary: {
            final_top10: [{ strategy_id: "RSI", timeframe: "60", net_profit: 100, trades: 5, bar_count: 720 }],
            buy_and_hold: { net_profit: 50, trades: 1, bar_count: 720 },
            lookback_days: 30,
          },
        }),
      );
      return;
    }
    if (url.includes("/backtest/fleet/history")) {
      await route.fulfill(json({ runs: [], total: 0 }));
      return;
    }
    if (url.includes("/backtest/fleet/active")) {
      if (fleetStatus === "running") {
        fleetPolls += 1;
        if (fleetPolls >= 2) fleetStatus = "complete";
      }
      const running = fleetStatus === "running";
      const complete = fleetStatus === "complete";
      await route.fulfill(
        json({
          status: complete ? "complete" : running ? "running" : "idle",
          progress_pct: complete ? 100 : running ? 50 : 0,
          total_combinations: 3,
          completed: complete ? 3 : running ? 1 : 0,
          phase: complete ? "done" : "pass1",
          summary: complete
            ? {
                final_top10: [
                  { strategy_id: "RSI", timeframe: "60", net_profit: 100, trades: 5, bar_count: 720 },
                ],
                buy_and_hold: { net_profit: 50, trades: 1, bar_count: 720 },
                lookback_days: 30,
              }
            : undefined,
        }),
      );
      return;
    }
    if (url.includes("/backtest/fleet/latest")) {
      await route.fulfill(
        json({
          rankings:
            fleetStatus === "complete"
              ? [{ strategy_id: "RSI", timeframe: "60", net_profit: 100, trades: 5, rank: 1 }]
              : [],
          total_rankings: fleetStatus === "complete" ? 1 : 0,
        }),
      );
      return;
    }
    if (url.includes("/backtest/exchange-fees")) {
      await route.fulfill(
        json({
          tier: "retail_default",
          exchanges: [
            {
              exchange_id: "kraken",
              taker_pct: 0.0026,
              maker_pct: 0.0016,
              tier: "retail_default",
              source_url: "",
            },
            {
              exchange_id: "binanceus",
              taker_pct: 0.0001,
              maker_pct: 0,
              tier: "retail_default",
              source_url: "",
            },
          ],
        }),
      );
      return;
    }
    if (url.includes("/backtest/fleet") && method === "POST") {
      fleetStatus = "running";
      fleetPolls = 0;
      await route.fulfill(json({ status: "running", progress_pct: 0, total_combinations: 3 }));
      return;
    }
    if (url.includes("/backtest") && method === "POST") {
      await route.fulfill(
        json({
          result: {
            strategy: "multi-tf-example",
            pair: "BTC/USD",
            total_trades: 2,
            profit_total: 10,
            profit_total_pct: 0.01,
            max_drawdown: 0.01,
            trades: [
              { pair: "BTC/USD", profit_abs: 12 },
              { pair: "BTC/USD", profit_abs: -2 },
            ],
          },
          metrics: {
            sharpe_ratio: 1.2,
            sortino_ratio: 1.5,
            calmar_ratio: 2,
            win_rate: 0.5,
            max_drawdown: 0.01,
          },
          equity_curve: [
            { time: 1700000000, value: 1012 },
            { time: 1700003600, value: 1010 },
          ],
        }),
      );
      return;
    }
    if (url.includes("/debug/logs")) {
      await route.fulfill(json({ logs: ["boot ok", "dry-run active"] }));
      return;
    }
    if (url.includes("/portfolio/performance")) {
      const range = new URL(url).searchParams.get("range") ?? "1y";
      const count =
        range === "24h" ? 25 : range === "7d" ? 7 : range === "14d" ? 14 : range === "1m" ? 30 : range === "3m" ? 91 : range === "6m" ? 182 : 365;
      const step = range === "24h" ? 3_600 : 86_400;
      const now = Math.floor(Date.now() / 1000);
      const points = Array.from({ length: count + 1 }, (_, i) => ({
        time: now - (count - i) * step,
        value: 42_000 + i * 150,
      }));
      const top10 = points.map((p, i) => ({ time: p.time, value: p.value * (0.98 + i * 0.0001) }));
      await route.fulfill(
        json({
          range,
          points,
          top10_index: top10,
          comparison: {
            portfolio_return_pct: 12.5,
            top10_return_pct: 10.2,
            alpha_pct: 2.3,
            symbols: ["BTC", "ETH", "SOL", "BNB", "XRP", "ADA", "DOGE", "AVAX", "DOT", "LINK"],
          },
          top10_symbols: ["BTC", "ETH", "SOL", "BNB", "XRP", "ADA", "DOGE", "AVAX", "DOT", "LINK"],
          asset: "BTC",
          quantity: 1,
        }),
      );
      return;
    }
    if (url.includes("/portfolio/overview")) {
      await route.fulfill(
        json({
          net_worth_usd: 98_000,
          daily_pnl_usd: 850,
          daily_pnl_pct: 0.0087,
          health_score: 82,
          max_drawdown_pct: 0.08,
          holdings: [
            {
              asset: "BTC",
              quantity: 1,
              price_usd: 98000,
              value_usd: 98000,
              cost_basis_usd: 42000,
              unrealized_pnl_usd: 56000,
              pct_change: 1.33,
              tag: "L1",
            },
          ],
          allocation: [{ asset: "BTC", value_usd: 98000, pct: 1 }],
          pl_breakdown: { realized_usd: 0, unrealized_usd: 56000, total_usd: 56000 },
          periods: [{ label: "daily", pnl_usd: 850, pnl_pct: 0.0087 }],
          comparisons: [
            { label: "mom", title: "Month over month", pnl_usd: 4200, pnl_pct: 0.045 },
            { label: "yoy", title: "Year over year", pnl_usd: 56000, pnl_pct: 1.33 },
          ],
          accounts: [
            { account_id: 1, exchange: "kraken", label: "default", account_type: "spot", total_usd: 98000, holdings_count: 1 },
          ],
          performance_goal: {
            label: "Grow portfolio to target value",
            goal_type: "portfolio_growth",
            horizon_months: 12,
            target_return_pct: 0,
            target_net_worth_usd: 120_000,
            progress_pct: 0.82,
            remaining_usd: 22_000,
            current_net_worth_usd: 98_000,
          },
          equity_curve: mockEquity1y,
          performance_ranges: ["1y", "6m", "3m", "1m", "14d", "7d", "24h"],
          performance_range_default: "1y",
          snapshot_dates: ["2026-06-24", "2026-06-25"],
          bot: sampleDashboard,
        }),
      );
      return;
    }
    if (url.includes("/portfolio/heatmap")) {
      await route.fulfill(json({ rows: [{ asset: "BTC", return_pct: 5, volatility_pct: 5 }] }));
      return;
    }
    if (url.includes("/portfolio/goals") && method === "PUT") {
      const body = route.request().postDataJSON() as Record<string, unknown>;
      await route.fulfill(
        json({
          goal: {
            label: body.label ?? "Goal",
            goal_type: body.goal_type ?? "portfolio_growth",
            horizon_months: body.horizon_months ?? 12,
            target_return_pct: body.target_return_pct ?? 0,
            target_net_worth_usd: body.target_net_worth_usd ?? 120_000,
            progress_pct: 0.5,
            remaining_usd: 10_000,
            current_net_worth_usd: 98_000,
          },
        }),
      );
      return;
    }
    if (url.includes("/portfolio/history")) {
      await route.fulfill(
        json({
          date: "2026-06-24",
          snapshot: { total_usd: 1475, holdings: [{ asset: "BTC", value_usd: 475 }] },
        }),
      );
      return;
    }
    if (url.includes("/portfolio/export")) {
      await route.fulfill({ status: 200, contentType: "text/csv", body: "asset,quantity\nBTC,0.01" });
      return;
    }
    if (url.includes("/portfolio/sync") && method === "POST") {
      await route.fulfill(json({ total_usd: 1500, mode: "dry-run" }));
      return;
    }
    if (url.includes("/notifications/inbox")) {
      await route.fulfill(json({ items: [{ id: 1, category: "daily_pl", title: "Daily", body: "P/L ok", created_at: "2026-06-25", read: false }] }));
      return;
    }
    if (url.includes("/strategies") && !url.includes("/params")) {
      if (url.includes("/export")) {
        await route.fulfill(json({ json: '{"id":"smart-dca"}' }));
        return;
      }
      await route.fulfill(
        json({
          strategies: [
            { id: "smart-dca", description: "DCA", kind: "dca", timeframes: ["1h"] },
            { id: "grid-trading", description: "Grid", kind: "grid", timeframes: ["5m"] },
          ],
        }),
      );
      return;
    }
    if (url.includes("/bots")) {
      if (url.includes("/bots/ohlcv/warmup/active") && method === "GET") {
        await route.fulfill(
          json({
            status: "complete",
            progress_pct: 100,
            total_series: 2,
            completed_series: 2,
            bars_cached: 720,
            bars_downloaded: 0,
            messages: ["Cache hit: mock bots already warmed"],
          }),
        );
        return;
      }
      if (url.includes("/bots/ohlcv/warmup") && method === "POST") {
        await route.fulfill(
          json({
            id: "mock-warmup",
            status: "complete",
            progress_pct: 100,
            total_series: mockBots.length,
            completed_series: mockBots.length,
            bars_cached: 720,
            bars_downloaded: 0,
            messages: ["Mock OHLCV warmup complete"],
          }),
        );
        return;
      }
      if (url.includes("/bots/ohlcv/cache") && method === "GET") {
        await route.fulfill(
          json({
            bot_scoped: true,
            bot_count: mockBots.length,
            unique_series: mockBots.length,
            series: mockBots.map((b) => ({
              pair: b.pair,
              timeframe: b.timeframe ?? "60",
              cached_bars: 720,
              expected_bars: 720,
              coverage_pct: 100,
              bots: [b.label],
            })),
          }),
        );
        return;
      }
      if (url.includes("/bots/limits") && method === "GET") {
        await route.fulfill(
          json({
            max_bots_total: 500,
            max_enabled_bots: 50,
            max_sub_minute_enabled: 3,
            max_1s_enabled: 1,
            sub_minute_intervals: ["1S", "5S", "15S", "30S"],
            bot_count: mockBots.length,
            enabled_count: mockBots.filter((b) => b.enabled).length,
            paper: true,
          }),
        );
        return;
      }
      const forceMatch = url.match(/\/bots\/(\d+)\/force/);
      if (forceMatch && method === "POST") {
        const body = route.request().postDataJSON() as { side: string };
        await route.fulfill(
          json({
            bot_id: Number(forceMatch[1]),
            side: body.side,
            amount: 0.001,
            order: { ok: true, simulated: true },
          }),
        );
        return;
      }
      const enabledMatch = url.match(/\/bots\/(\d+)\/enabled/);
      if (enabledMatch && method === "PUT") {
        const botId = Number(enabledMatch[1]);
        const body = route.request().postDataJSON() as { enabled: boolean };
        mockBots = mockBots.map((b) => (b.id === botId ? { ...b, enabled: body.enabled } : b));
        await route.fulfill(json({ bots: mockBots }));
        return;
      }
      const limitsMatch = url.match(/\/bots\/(\d+)\/equity-limits$/);
      if (limitsMatch && method === "GET") {
        const bot = mockBots.find((b) => b.id === Number(limitsMatch[1]));
        const pair = bot?.pair ?? "BTC/USD";
        await route.fulfill(
          json({
            base: { symbol: pair.split("/")[0] ?? "BTC", max: 1.5 },
            quote: { symbol: pair.split("/")[1] ?? "USD", max: 25_000 },
            portfolio_usd: 100_000,
          }),
        );
        return;
      }
      const botMatch = url.match(/\/bots\/(\d+)$/);
      if (botMatch && method === "GET") {
        const botId = Number(botMatch[1]);
        const bot = mockBots.find((b) => b.id === botId);
        if (!bot) {
          await route.fulfill({ status: 404, contentType: "application/json", body: '{"detail":"bot not found"}' });
          return;
        }
        const chart = mockEquityCurve(30, bot.pair.startsWith("BTC") ? 98_000 : 3_200);
        const ohlcv = chart.map((p) => ({
          time: p.time,
          open: p.value * 0.998,
          high: p.value * 1.002,
          low: p.value * 0.996,
          close: p.value,
          volume: 1000,
        }));
        const trades = [
          {
            pair: bot.pair,
            side: "buy",
            stake_usd: 100,
            pnl_usd: 0,
            created_at: new Date(Date.now() - 86_400_000).toISOString(),
          },
          {
            pair: bot.pair,
            side: "sell",
            stake_usd: 100,
            pnl_usd: -3,
            created_at: new Date(Date.now() - 43_200_000).toISOString(),
          },
        ];
        const markers = trades.map((t) => ({
          time: Math.floor(new Date(t.created_at).getTime() / 1000),
          side: t.side,
          pnl_usd: t.side === "sell" ? t.pnl_usd : null,
          pnl_pct: t.side === "sell" ? -3 : null,
        }));
        const regions =
          markers.length >= 2
            ? [
                {
                  time_start: markers[0]!.time,
                  time_end: markers[1]!.time,
                  entry_price: ohlcv[0]?.close ?? chart[0]?.value ?? 0,
                  exit_price: ohlcv[ohlcv.length - 1]?.close ?? chart[chart.length - 1]?.value ?? 0,
                  profitable: false,
                  pnl_usd: -3,
                },
              ]
            : [];
        await route.fulfill(
          json({
            bot: { ...bot, equity_mode: "quote", equity_input: bot.equity_usd, ta_params: { timeperiod: 14 } },
            pnl_usd: Number(bot.pnl_usd ?? 0),
            pnl_pct: Number(bot.pnl_pct ?? 0),
            realized_pnl_usd: Number(bot.realized_pnl_usd ?? 0),
            unrealized_pnl_usd: Number(bot.unrealized_pnl_usd ?? 0),
            trade_count: Number(bot.trade_count ?? 0),
            trades,
            simulated_trades: trades.map((t) => ({ ...t, simulated: true })),
            chart,
            ohlcv,
            trade_markers: markers,
            simulated_markers: markers,
            trade_regions: regions,
            simulated_regions: regions,
            equity_limits: {
              base: { symbol: bot.pair.split("/")[0] ?? "BTC", max: 1.5 },
              quote: { symbol: bot.pair.split("/")[1] ?? "USD", max: 25_000 },
              portfolio_usd: 100_000,
            },
            strategy_params: { timeperiod: 14 },
            available_timeframes: ["1", "60", "1D", "1W"],
            timeframe_labels: { "1": "1 minute", "60": "1 hour", "1D": "1 day", "1W": "1 week" },
            param_specs: [{ key: "timeperiod", label: "Period", default: 14 }],
            backtest_top5: [
              { indicator: "RSI", ta_function: "RSI", profit_total: 24.5, timeframe: "60" },
              { indicator: "MACD", ta_function: "MACD", profit_total: 18.2, timeframe: "60" },
            ],
          }),
        );
        return;
      }
      if (botMatch && method === "PUT") {
        const botId = Number(botMatch[1]);
        const body = route.request().postDataJSON() as Record<string, unknown>;
        mockBots = mockBots.map((b) =>
          b.id === botId
            ? {
                ...b,
                label: String(body.label ?? b.label),
                strategy_id: String(body.strategy_id ?? b.strategy_id),
                pair: String(body.pair ?? b.pair),
                equity_usd: Number(body.equity_usd ?? b.equity_usd),
                timeframe: String(body.timeframe ?? b.timeframe ?? "1h"),
              }
            : b,
        );
        await route.fulfill(json({ bots: mockBots }));
        return;
      }
      if (botMatch && method === "DELETE") {
        const botId = Number(botMatch[1]);
        mockBots = mockBots.filter((b) => b.id !== botId);
        await route.fulfill(json({ bots: mockBots }));
        return;
      }
      if (method === "POST") {
        const body = route.request().postDataJSON() as {
          label: string;
          strategy_id?: string;
          pair?: string;
          equity_usd?: number;
          enabled?: boolean;
          timeframe?: string;
        };
        const id = Math.max(0, ...mockBots.map((b) => b.id)) + 1;
        const newBot = {
          id,
          label: body.label,
          strategy_id: body.strategy_id ?? "RSI",
          pair: body.pair ?? "BTC/USD",
          enabled: body.enabled ?? false,
          equity_usd: body.equity_usd ?? 1000,
          timeframe: body.timeframe ?? "60",
          engine: "native",
          exchange: "kraken",
          realized_pnl_usd: 0,
          unrealized_pnl_usd: 0,
          pnl_usd: 0,
          pnl_pct: 0,
          trade_count: 0,
        };
        mockBots = [...mockBots, newBot];
        await route.fulfill(json({ id, bots: mockBots }));
        return;
      }
      await route.fulfill(json({ bots: mockBots, enabled_count: mockBots.filter((b) => b.enabled).length }));
      return;
    }
    if (url.includes("/hyperopt")) {
      await route.fulfill(json({ status: "queued", strategy: "smart-dca" }));
      return;
    }
    if (url.includes("/api/v1/watchlist")) {
      await route.fulfill(json({ items: [{ pair: "SOL/USD", alert_price_pct: 0.05, alert_pl_usd: 50 }] }));
      return;
    }
    if (url.includes("/export/tax")) {
      await route.fulfill({ status: 200, contentType: "text/csv", body: "pair,realized_gl_usd\nBTC/USD,12" });
      return;
    }
    if (url.includes("/export/hub")) {
      await route.fulfill(
        json({
          exports: [
            { id: "portfolio_csv", path: "/api/v1/portfolio/export", format: "csv" },
            { id: "tax_csv", path: "/api/v1/export/tax", format: "csv" },
          ],
          account_id: 1,
          trade_count: 2,
        }),
      );
      return;
    }
    if (url.includes("/export/bundle") || url.includes("/export/settings")) {
      await route.fulfill(json({ portfolio: {}, strategy_params: {}, disclaimer: "Not tax advice" }));
      return;
    }
    if (url.includes("/research/correlation")) {
      await route.fulfill(
        json({
          correlation: { assets: ["BTC"], matrix: [[1]] },
          suggestions: ["Add ETH for diversification"],
        }),
      );
      return;
    }
    if (url.includes("/research/walk-forward")) {
      await route.fulfill(json({ status: "complete", fold_count: 2, folds: [], avg_test_pnl: 5 }));
      return;
    }
    if (url.includes("/research/monte-carlo") || url.includes("/research/portfolio-monte-carlo")) {
      await route.fulfill(json({ p5: 1, p50: 10, p95: 20 }));
      return;
    }
    if (url.includes("/research/hyperopt-heatmap")) {
      await route.fulfill(json({ cells: [{ x: 1, y: 2, value: 0.5 }] }));
      return;
    }
    if (url.includes("/strategies/exit-rules")) {
      if (method === "PUT") {
        await route.fulfill(
          json({
            trailing_stop_pct: 0.04,
            scale_out_pct: 0.5,
            scale_in_enabled: false,
            scale_out_enabled: true,
          }),
        );
        return;
      }
      await route.fulfill(
        json({
          trailing_stop_pct: 0.03,
          scale_out_pct: 0.5,
          scale_in_enabled: false,
          scale_out_enabled: true,
        }),
      );
      return;
    }
    if (url.includes("/health")) {
      await route.fulfill(json({ status: "ok", dry_run: true, paused: risk.paused }));
      return;
    }
    if (url.includes("/scanner/settings")) {
      if (method === "PUT") {
        await route.fulfill(
          json({
            interval_minutes: 30,
            min_volume_usd: 100000,
            min_gain_pct: 0.02,
            min_uniformity: 0.55,
            universe_filter: "kraken-spot",
            trendspotter_boost: true,
          }),
        );
        return;
      }
      await route.fulfill(
        json({
          interval_minutes: 60,
          min_volume_usd: 100000,
          min_gain_pct: 0.02,
          min_uniformity: 0.55,
          universe_filter: "kraken-spot",
          trendspotter_boost: true,
        }),
      );
      return;
    }
    if (url.includes("/portfolio/rebalance")) {
      await route.fulfill(
        json({
          targets: [{ asset: "BTC", target_pct: 0.6 }],
          suggestions: [{ asset: "BTC", current_pct: 0.33, target_pct: 0.6, delta_usd: 400, action: "buy", manual_only: true }],
          manual_only: true,
          disclaimer: "Suggestions only",
        }),
      );
      return;
    }
    if (url.includes("/portfolio/arbitrage")) {
      await route.fulfill(
        json({
          alerts: [{ pair: "BTC/USD", spread_pct: 0.0024, buy_exchange: "kraken", sell_exchange: "binanceus", informational_only: true }],
          disclaimer: "Informational only",
          auto_trade: false,
          count: 1,
        }),
      );
      return;
    }
    if (url.includes("/exchanges/registry")) {
      await route.fulfill(
        json({
          version: 2,
          exchanges: [
            { id: "kraken", brand: "Kraken", tier: "A", portfolio_enabled: true, trading_enabled: true, configured: false },
            { id: "binanceus", brand: "Binance.US", tier: "A", portfolio_enabled: true, trading_enabled: true, configured: false },
            { id: "coinbaseadvanced", brand: "Coinbase Advanced", tier: "B", portfolio_enabled: true, trading_enabled: false, configured: false },
            { id: "gemini", brand: "Gemini", tier: "B", portfolio_enabled: true, trading_enabled: false, configured: false },
          ],
        }),
      );
      return;
    }
    if (url.includes("/portfolio/sync-all")) {
      await route.fulfill(json({ kraken: { mode: "dry-run" }, binanceus: { mode: "dry-run" }, registry_version: 2, staggered: true, exchange_count: 7 }));
      return;
    }
    if (url.includes("/billing/dashboard")) {
      await route.fulfill(
        json({
          enrollment: { enrolled: 0, license_rate_pct: 0.05 },
          license_status: { suspended: 0, grace_day: 0 },
          lifetime: { lifetime_gross_profit_usd: 65, lifetime_license_fees_usd: 7.8, lifetime_net_benefit_usd: 57.2 },
          current_period: "2026-06",
          period_rollup: { gross_profit_usd: 65, license_fee_usd: 3.25, net_benefit_usd: 61.75 },
          line_items: [{ pair: "BTC/USD", gross_profit_usd: 25, license_fee_usd: 1.25, rule_applied: "net_positive" }],
          statements: [{ period: "2026-06", license_fee_usd: 3.25 }],
          can_trade_live: true,
          dry_run_fee_preview: { rate_pct: 0.05, sample_profit_usd: 100, sample_fee_usd: 5 },
          disclaimer: "Software license only.",
          net_loss_equals_zero_fee: true,
          payment_auto_verify: true,
          billing_eligibility: {
            first_profitable_trade_at: "2025-01-01T00:00:00+00:00",
            billing_starts_at: "2025-02-01T00:00:00+00:00",
            billing_active: true,
            awaiting_first_profit: false,
            trial_period: false,
            delay_months: 1,
          },
        }),
      );
      return;
    }
    if (url.includes("/billing/payment/assets")) {
      await route.fulfill(
        json({
          assets: [
            { asset: "BTC", label: "Bitcoin (BTC)", chain: "bitcoin", enabled: true },
            { asset: "USDC", label: "USD Coin (USDC)", chain: "base", enabled: true },
            { asset: "USDT", label: "Tether (USDT)", chain: "base", enabled: true },
          ],
        }),
      );
      return;
    }
    if (url.includes("/billing/settlement") || url.includes("/billing/payment/start")) {
      const body = route.request().postDataJSON?.() as { asset?: string } | undefined;
      const asset = body?.asset ?? "BTC";
      const isStable = asset === "USDC" || asset === "USDT";
      await route.fulfill(
        json({
          id: "pay-mock001",
          payment_id: "pay-mock001",
          period: "2026-06",
          amount_usd: 3.25,
          amount_to_send: isStable ? 3.250421 : 0.00003425,
          amount_btc: isStable ? 0 : 0.00003425,
          amount_sats: isStable ? 0 : 3425,
          amount_atomic: isStable ? 3250421 : 3425,
          payment_reference: "abc123def456",
          status: "pending",
          asset,
          chain: isStable ? "base" : "bitcoin",
          chain_id: isStable ? 8453 : null,
          address: isStable ? "0xdead000000000000000000000000000000beef" : "bc1q-sample",
          qr_payload: isStable
            ? "ethereum:0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913@8453/transfer?address=0xdead&uint256=3250421"
            : "bitcoin:bc1q-sample?amount=0.00003425",
          user_initiated_only: true,
          auto_withdraw: false,
          auto_verify: true,
          payment_instructions: isStable
            ? "Send exactly 3.250421 USDC on Base"
            : "Send exactly 0.00003425 BTC",
          disclaimer: "User-initiated only",
          grace_period_days: 7,
        }),
      );
      return;
    }
    if (url.match(/\/billing\/payment\/status\//)) {
      await route.fulfill(
        json({
          verified: true,
          status: "confirmed",
          payment: {
            id: "pay-mock001",
            period: "2026-06",
            amount_usd: 3.25,
            status: "confirmed",
            licensed_until: "2026-07-31T23:59:59+00:00",
          },
        }),
      );
      return;
    }
    if (url.includes("/billing/")) {
      await route.fulfill(json({ ok: true, enrollment: { enrolled: 1 } }));
      return;
    }
    if (url.includes("/ai/recommendations")) {
      await route.fulfill(
        json({
          recommendations: [
            { strategy_id: "strong-uptrend-scanner", score: 75, reasons: ["LTS active"], requires_backtest: true },
          ],
          disclaimer: "Not financial advice.",
        }),
      );
      return;
    }
    if (url.includes("/ai/curated-library")) {
      await route.fulfill(
        json({
          version: "2026.06.1",
          presets: [{ id: "curated-lts-momentum", label: "LTS Momentum", strategy_id: "strong-uptrend-scanner", version: "2026.06.1" }],
          user_uploads: false,
        }),
      );
      return;
    }
    if (url.includes("/growth/referral")) {
      await route.fulfill(json({ code: "ABCD1234EF", pseudonymous_only: true }));
      return;
    }
    if (url.includes("/growth/leaderboard")) {
      await route.fulfill(json({ rows: [{ pseudonym: "trader-abc", score_usd: 1500 }], no_pii: true }));
      return;
    }
    if (url.includes("/billing/boost-mode")) {
      await route.fulfill(json({ boost_mode: true, license_rate_pct: 0.15 }));
      return;
    }
    if (url.includes("/ai/") || url.includes("/growth/")) {
      await route.fulfill(json({ ok: true }));
      return;
    }
    if (url.includes("/scanner/watchlist")) {
      await route.fulfill(json({ pairs: ["ETH/USD"] }));
      return;
    }
    if (url.includes("/scanner/snapshot") || url.includes("/scanner/run")) {
      await route.fulfill(
        json({
          version: "1",
          generated_at: "2026-06-25T12:00:00+00:00",
          scan_id: 1,
          opportunities: [
            {
              rank: 1,
              pair: "ETH/USD",
              uniformity: 0.72,
              gain_pct: 0.05,
              volume_score: 1,
              entry_signal: true,
              sparkline: [100, 101, 102, 103],
            },
          ],
        }),
      );
      return;
    }
    if (url.includes("/platform/forager")) {
      await route.fulfill(json({ pairs: [{ pair: "BTC/USD", forager_score: 0.8 }], pair_count: 1 }));
      return;
    }
    if (url.includes("/platform/funding")) {
      await route.fulfill(json({ rates: [{ exchange: "kraken", rate: 0.0001 }], rows: [] }));
      return;
    }
    if (url.includes("/platform/postgres")) {
      await route.fulfill(json({ enabled: false, sqlite_mvp: true, schema_exists: false }));
      return;
    }
    if (url.includes("/platform/")) {
      await route.fulfill(json({ ok: true }));
      return;
    }
    await route.fulfill({ status: 404, body: "not mocked" });
  });
}
