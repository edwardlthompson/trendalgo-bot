import { beforeEach, describe, expect, it, vi } from "vitest";
import en from "./locales/en.json";
import { bootstrapApp } from "./appBootstrap";
import type { AppShellCallbacks } from "./AppShell";

const messages = en as Record<string, string>;

vi.mock("./AppShell", () => ({
  createAppShell: vi.fn(),
}));

vi.mock("./api/client", () => ({
  fetchDashboard: vi.fn(() =>
    Promise.resolve({
      dry_run: true,
      equity_usd: 1000,
      open_trades: [],
      open_orders: [],
      bot_count: 1,
      strategy_id: "multi-tf-example",
      pair: "BTC/USD",
      risk: { can_trade: true, equity_usd: 1000, drawdown_pct: 0, paused: false },
    }),
  ),
  fetchPairs: vi.fn(() => Promise.resolve(["BTC/USD"])),
  fetchStrategyParams: vi.fn(() =>
    Promise.resolve({ strategy_id: "multi-tf-example", params: { rsi_entry: 35 } }),
  ),
  fetchLatestBacktest: vi.fn(() =>
    Promise.resolve({ result: null, metrics: null, equity_curve: [] }),
  ),
  fetchDebugLogs: vi.fn(() => Promise.resolve(["boot"])),
  pauseTrading: vi.fn(() => Promise.resolve()),
  resumeTrading: vi.fn(() => Promise.resolve()),
  runBacktest: vi.fn(() =>
    Promise.resolve({
      result: { strategy: "multi-tf-example", pair: "BTC/USD", total_trades: 1, profit_total: 5, trades: [] },
      metrics: { sharpe_ratio: 1 },
      equity_curve: [{ time: 1, value: 1005 }],
    }),
  ),
  startFleetBacktest: vi.fn(() =>
    Promise.resolve({ status: "running", progress_pct: 0, total_combinations: 3 }),
  ),
  fetchFleetActive: vi.fn(() => Promise.resolve({ status: "idle" })),
  fetchFleetLatest: vi.fn(() => Promise.resolve({ rankings: [], total_rankings: 0 })),
  fetchExchangeFees: vi.fn(() =>
    Promise.resolve({
      tier: "retail_default",
      exchanges: [{ exchange_id: "kraken", taker_pct: 0.0026, maker_pct: 0.0016, tier: "retail_default", source_url: "" }],
    }),
  ),
  saveStrategyParams: vi.fn(() => Promise.resolve()),
  connectLiveSocket: vi.fn(() => null),
  fetchScannerSnapshot: vi.fn(() => Promise.resolve({ pairs: [], scanned_at: null })),
  fetchScannerSettings: vi.fn(() =>
    Promise.resolve({
      interval_minutes: 15,
      min_volume_usd: 100000,
      min_gain_pct: 2,
      min_uniformity: 0.5,
      max_pairs: 10,
      enabled: true,
    }),
  ),
  fetchScannerWatchlist: vi.fn(() => Promise.resolve([])),
  fetchPortfolioOverview: vi.fn(() =>
    Promise.resolve({
      net_worth_usd: 1000,
      daily_pnl_usd: 0,
      daily_pnl_pct: 0,
      health_score: 80,
      max_drawdown_pct: 0,
      holdings: [],
      allocation: [],
      pl_breakdown: [],
      periods: {},
      equity_curve: [],
      snapshot_dates: [],
    }),
  ),
  fetchPortfolioPerformance: vi.fn(() =>
    Promise.resolve({
      range: "1y",
      points: [
        { time: 1, value: 42000 },
        { time: 2, value: 98000 },
      ],
      top10_index: [
        { time: 1, value: 42000 },
        { time: 2, value: 95000 },
      ],
      comparison: { portfolio_return_pct: 10, top10_return_pct: 8, alpha_pct: 2 },
    }),
  ),
  fetchPortfolioHeatmap: vi.fn(() => Promise.resolve({ rows: [] })),
  fetchNotificationInbox: vi.fn(() => Promise.resolve({ items: [] })),
  fetchPortfolioRebalance: vi.fn(() => Promise.resolve({ suggestions: [] })),
  fetchPortfolioArbitrage: vi.fn(() => Promise.resolve({ alerts: [], disclaimer: "" })),
  fetchExchangeRegistry: vi.fn(() => Promise.resolve({ exchanges: [] })),
  fetchTaLibrary: vi.fn(() =>
    Promise.resolve({
      categories: [],
      count: 0,
    }),
  ),
  fetchTaGlossary: vi.fn(() => Promise.resolve({ entries: [], count: 0 })),
  fetchBotEquityLimits: vi.fn(() =>
    Promise.resolve({
      base: { symbol: "BTC", max: 1 },
      quote: { symbol: "USD", max: 10000 },
      portfolio_usd: 100000,
    }),
  ),
  fetchExchangePairs: vi.fn(() => Promise.resolve({ pairs: ["BTC/USD"] })),
  fetchBotLimits: vi.fn(() =>
    Promise.resolve({
      max_bots_total: 500,
      max_enabled_bots: 50,
      max_sub_minute_enabled: 3,
      max_1s_enabled: 1,
      sub_minute_intervals: ["1S", "5S", "15S", "30S"],
      bot_count: 1,
      enabled_count: 1,
      paper: true,
    }),
  ),
  addBot: vi.fn(() => Promise.resolve({ id: 2, bots: [] })),
  fetchExportHub: vi.fn(() => Promise.resolve({ exports: [] })),
  fetchResearchCorrelation: vi.fn(() => Promise.resolve(null)),
  fetchExitRules: vi.fn(() => Promise.resolve({ trailing_stop_pct: 0.03, scale_out_pct: 0.5 })),
  fetchBillingDashboard: vi.fn(() => Promise.resolve({ period: "2026-06", status: "draft" })),
  fetchPlatformForager: vi.fn(() => Promise.resolve({ pairs: [] })),
  fetchPlatformFunding: vi.fn(() => Promise.resolve({ rates: [] })),
  fetchPlatformPostgres: vi.fn(() => Promise.resolve({ enabled: false })),
}));

vi.mock("./about/aboutSession", () => ({
  handleRestartGuard: vi.fn(() => false),
  checkForUpdates: vi.fn(() => Promise.resolve(messages["about.update.current"])),
}));

vi.mock("./about/donations", () => ({
  loadDonations: vi.fn(() => Promise.resolve({ enabled: false, message: "", links: [] })),
}));

vi.mock("./theme", () => ({
  initTheme: vi.fn(),
  subscribeThemeChange: vi.fn(),
}));

vi.mock("./i18n", () => ({
  t: vi.fn((key: string) => messages[key] ?? key),
}));

import { createAppShell } from "./AppShell";
import * as api from "./api/client";

const mockedCreateAppShell = vi.mocked(createAppShell);

describe("bootstrapApp API wiring", () => {
  let handlers: AppShellCallbacks | undefined;

  beforeEach(() => {
    vi.clearAllMocks();
    handlers = undefined;
    mockedCreateAppShell.mockImplementation((_root, _state, h) => {
      handlers = h;
    });
    Object.defineProperty(navigator, "serviceWorker", {
      configurable: true,
      value: { register: vi.fn(() => Promise.resolve()) },
    });
  });

  it("loads dashboard from API on bootstrap", async () => {
    const root = document.createElement("div");
    bootstrapApp(root);
    await vi.waitFor(() =>
      expect(
        mockedCreateAppShell.mock.calls.some(([, state]) => state.apiOnline === true),
      ).toBe(true),
    );
    expect(api.fetchDashboard).toHaveBeenCalled();
  });

  it("pauses trading via API handler", async () => {
    const root = document.createElement("div");
    bootstrapApp(root);
    await vi.waitFor(() => expect(handlers).toBeDefined());
    handlers?.onPause?.();
    await vi.waitFor(() => expect(api.pauseTrading).toHaveBeenCalled());
  });

  it("runs fleet backtest via API handler", async () => {
    const root = document.createElement("div");
    bootstrapApp(root);
    await vi.waitFor(() =>
      expect(
        mockedCreateAppShell.mock.calls.some(([, state]) => state.dashboard !== null),
      ).toBe(true),
    );
    handlers?.onRunBacktest?.();
    await vi.waitFor(() => expect(api.startFleetBacktest).toHaveBeenCalled());
  });
});
