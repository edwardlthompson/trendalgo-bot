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
  saveStrategyParams: vi.fn(() => Promise.resolve()),
  connectLiveSocket: vi.fn(() => null),
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

  it("runs backtest via API handler", async () => {
    const root = document.createElement("div");
    bootstrapApp(root);
    await vi.waitFor(() =>
      expect(
        mockedCreateAppShell.mock.calls.some(([, state]) => state.dashboard !== null),
      ).toBe(true),
    );
    handlers?.onRunBacktest?.();
    await vi.waitFor(() => expect(api.runBacktest).toHaveBeenCalled());
  });
});
