import type { Page, Route } from "@playwright/test";

const sampleDashboard = {
  dry_run: true,
  equity_usd: 1000,
  open_trades: [],
  open_orders: [],
  bot_count: 1,
  strategy_id: "multi-tf-example",
  pair: "BTC/USD",
  bots: [
    { id: 1, label: "Bot-1", strategy_id: "multi-tf-example", pair: "BTC/USD", enabled: true, equity_usd: 1000 },
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

function json(body: unknown): { status: number; contentType: string; body: string } {
  return {
    status: 200,
    contentType: "application/json",
    body: JSON.stringify(body),
  };
}

export async function mockTrendAlgoApi(page: Page, paused = false): Promise<void> {
  const risk = { ...sampleDashboard.risk, paused, can_trade: !paused };
  const dashboard = { ...sampleDashboard, risk };

  await page.route(/\/api\/v1\//, async (route: Route) => {
    const url = route.request().url();
    const method = route.request().method();

    if (url.includes("/ws/live")) {
      await route.abort();
      return;
    }
    if (url.includes("/dashboard")) {
      await route.fulfill(json(dashboard));
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
    if (url.includes("/pairs")) {
      await route.fulfill(json({ pairs: ["BTC/USD", "ETH/USD"] }));
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
    if (url.includes("/portfolio/overview")) {
      await route.fulfill(
        json({
          net_worth_usd: 1500,
          daily_pnl_usd: 25,
          daily_pnl_pct: 0.016,
          health_score: 78,
          max_drawdown_pct: 0.02,
          holdings: [
            {
              asset: "BTC",
              quantity: 0.01,
              price_usd: 50000,
              value_usd: 500,
              cost_basis_usd: 450,
              unrealized_pnl_usd: 50,
              pct_change: 0.11,
              tag: "L1",
            },
          ],
          allocation: [{ asset: "BTC", value_usd: 500, pct: 0.33 }],
          pl_breakdown: { realized_usd: 0, unrealized_usd: 50, total_usd: 50 },
          periods: [{ label: "daily", pnl_usd: 25, pnl_pct: 0.016 }],
          comparisons: [
            { label: "mom", title: "Month over month", pnl_usd: 25, pnl_pct: 0.016 },
            { label: "yoy", title: "Year over year", pnl_usd: 100, pnl_pct: 0.08 },
          ],
          accounts: [
            { account_id: 1, exchange: "kraken", label: "default", account_type: "spot", total_usd: 1000, holdings_count: 2 },
            { account_id: 2, exchange: "binanceus", label: "default", account_type: "spot", total_usd: 500, holdings_count: 2 },
          ],
          performance_goal: {
            label: "Growth goal",
            target_net_worth_usd: 2000,
            progress_pct: 0.75,
            remaining_usd: 500,
            current_net_worth_usd: 1500,
          },
          equity_curve: [
            { time: 1700000000, value: 1475 },
            { time: 1700003600, value: 1500 },
          ],
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
    if (url.includes("/backtest/library")) {
      await route.fulfill(json({ runs: [{ id: 1, strategy: "multi-tf-example", pair: "BTC/USD", tag: "run-1", created_at: "2026-06-25" }] }));
      return;
    }
    if (url.includes("/bots")) {
      await route.fulfill(json({ bots: sampleDashboard.bots, enabled_count: 1 }));
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
          enrollment: { enrolled: 0, license_rate_pct: 0.12 },
          license_status: { suspended: 0, grace_day: 0 },
          lifetime: { lifetime_gross_profit_usd: 65, lifetime_license_fees_usd: 7.8, lifetime_net_benefit_usd: 57.2 },
          current_period: "2026-06",
          period_rollup: { gross_profit_usd: 65, license_fee_usd: 7.8, net_benefit_usd: 57.2 },
          line_items: [{ pair: "BTC/USD", gross_profit_usd: 25, license_fee_usd: 3, rule_applied: "net_positive" }],
          statements: [{ period: "2026-06", license_fee_usd: 7.8 }],
          can_trade_live: true,
          dry_run_fee_preview: { rate_pct: 0.12, sample_profit_usd: 100, sample_fee_usd: 12 },
          disclaimer: "Software license only.",
          net_loss_equals_zero_fee: true,
        }),
      );
      return;
    }
    if (url.includes("/billing/settlement")) {
      await route.fulfill(
        json({
          period: "2026-06",
          amount_usd: 7.8,
          asset: "BTC",
          address: "bc1q-sample",
          qr_payload: "bitcoin:bc1q-sample?amount=7.8",
          user_initiated_only: true,
          auto_withdraw: false,
          disclaimer: "User-initiated only",
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
    await route.fulfill({ status: 404, body: "not mocked" });
  });
}
