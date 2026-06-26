const API_BASE = "/api/v1";

export type DashboardData = {
  dry_run: boolean;
  equity_usd: number;
  open_trades: Array<Record<string, unknown>>;
  open_orders: Array<Record<string, unknown>>;
  bot_count: number;
  bots?: Array<{
    id: number;
    label: string;
    strategy_id: string;
    pair: string;
    enabled: boolean;
    equity_usd: number;
    engine?: string;
    exchange?: string;
  }>;
  strategy_id: string;
  pair: string;
  risk: Record<string, string | number | boolean>;
};

export type BacktestPayload = {
  result: {
    strategy: string;
    pair: string;
    total_trades: number;
    profit_total: number;
    profit_total_pct: number;
    max_drawdown: number | null;
    trades: Array<Record<string, unknown>>;
  } | null;
  metrics: Record<string, number> | null;
  equity_curve: Array<{ time: number; value: number }>;
  attribution?: Record<string, number>;
  library_id?: number;
  analysis?: Record<string, string>;
};

async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const resp = await fetch(`${API_BASE}${path}`, {
    headers: { Accept: "application/json", ...(init?.headers ?? {}) },
    ...init,
  });
  if (!resp.ok) {
    throw new Error(`API ${resp.status}`);
  }
  return (await resp.json()) as T;
}

export async function fetchDashboard(): Promise<DashboardData> {
  return apiFetch<DashboardData>("/dashboard");
}

export async function fetchRisk(): Promise<Record<string, string | number | boolean>> {
  return apiFetch("/risk");
}

export async function pauseTrading(): Promise<void> {
  await apiFetch("/risk/pause", { method: "POST" });
}

export async function resumeTrading(): Promise<void> {
  await apiFetch("/risk/resume", { method: "POST" });
}

export async function runBacktest(body: {
  strategy: string;
  pair: string;
  timeframe?: string;
  timerange?: string;
  slippage_pct?: number;
  fee_pct?: number;
  save_to_library?: boolean;
  tag?: string;
}): Promise<BacktestPayload> {
  return apiFetch<BacktestPayload>("/backtest", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}

export async function fetchLatestBacktest(): Promise<BacktestPayload> {
  return apiFetch<BacktestPayload>("/backtest/latest");
}

export async function fetchStrategyParams(
  strategyId: string,
): Promise<{ strategy_id: string; params: Record<string, number> }> {
  return apiFetch(`/strategies/${strategyId}/params`);
}

export async function saveStrategyParams(
  strategyId: string,
  params: Record<string, number>,
): Promise<void> {
  await apiFetch(`/strategies/${strategyId}/params`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ params }),
  });
}

export async function fetchDebugLogs(): Promise<string[]> {
  const data = await apiFetch<{ logs: string[] }>("/debug/logs");
  return data.logs;
}

export async function fetchPairs(): Promise<string[]> {
  const data = await apiFetch<{ pairs: string[] }>("/pairs");
  return data.pairs;
}

export type ScannerSnapshotPayload = {
  version: string;
  generated_at: string | null;
  scan_id: number;
  opportunities: Array<{
    rank: number;
    pair: string;
    uniformity: number;
    gain_pct: number;
    volume_score: number;
    entry_signal: boolean;
    sparkline: number[];
  }>;
};

export type ScannerSettingsPayload = {
  interval_minutes: number;
  min_volume_usd: number;
  min_gain_pct: number;
  min_uniformity: number;
  universe_filter: string;
  trendspotter_boost: boolean;
};

export async function fetchScannerSnapshot(): Promise<ScannerSnapshotPayload> {
  return apiFetch<ScannerSnapshotPayload>("/scanner/snapshot");
}

export async function runScannerScan(): Promise<ScannerSnapshotPayload> {
  return apiFetch<ScannerSnapshotPayload>("/scanner/run", { method: "POST" });
}

export async function fetchScannerSettings(): Promise<ScannerSettingsPayload> {
  return apiFetch<ScannerSettingsPayload>("/scanner/settings");
}

export async function saveScannerSettings(
  settings: ScannerSettingsPayload,
): Promise<ScannerSettingsPayload> {
  return apiFetch<ScannerSettingsPayload>("/scanner/settings", {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(settings),
  });
}

export async function fetchScannerWatchlist(): Promise<string[]> {
  const data = await apiFetch<{ pairs: string[] }>("/scanner/watchlist");
  return data.pairs;
}

export async function pinScannerPair(pair: string): Promise<string[]> {
  const data = await apiFetch<{ pairs: string[] }>("/scanner/watchlist", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ pair }),
  });
  return data.pairs;
}

export type PortfolioOverviewPayload = {
  net_worth_usd: number;
  daily_pnl_usd: number;
  daily_pnl_pct: number;
  health_score: number;
  max_drawdown_pct: number;
  holdings: Array<Record<string, unknown>>;
  allocation: Array<{ asset: string; value_usd: number; pct: number }>;
  pl_breakdown: { realized_usd: number; unrealized_usd: number; total_usd: number };
  periods: Array<{ label: string; pnl_usd: number; pnl_pct: number }>;
  comparisons?: Array<{ label: string; title: string; pnl_usd: number; pnl_pct: number }>;
  equity_curve: Array<{ time: number; value: number }>;
  snapshot_dates: string[];
  accounts?: Array<Record<string, unknown>>;
  performance_goal?: Record<string, unknown>;
  bot: Record<string, unknown>;
};

export type ExchangeRegistryPayload = {
  version: number;
  exchanges: Array<{
    id: string;
    brand: string;
    tier: string;
    portfolio_enabled: boolean;
    trading_enabled: boolean;
    configured?: boolean;
  }>;
};

export async function fetchExchangeRegistry(): Promise<ExchangeRegistryPayload> {
  return apiFetch<ExchangeRegistryPayload>("/exchanges/registry");
}

export async function syncPortfolioAll(): Promise<Record<string, unknown>> {
  return apiFetch("/portfolio/sync-all", { method: "POST" });
}

export async function fetchPortfolioRebalance(): Promise<{
  suggestions: Array<Record<string, unknown>>;
}> {
  return apiFetch("/portfolio/rebalance");
}

export async function applyPortfolioRebalance(): Promise<Record<string, unknown>> {
  return apiFetch("/portfolio/rebalance/apply", { method: "POST" });
}

export async function fetchPortfolioArbitrage(): Promise<{
  alerts: Array<Record<string, unknown>>;
  disclaimer: string;
}> {
  return apiFetch("/portfolio/arbitrage");
}

export async function createPublicDashboardShare(): Promise<{ token: string; url: string }> {
  return apiFetch("/portfolio/public-share", { method: "POST" });
}

export async function fetchPortfolioOverview(): Promise<PortfolioOverviewPayload> {
  return apiFetch<PortfolioOverviewPayload>("/portfolio/overview");
}

export async function syncPortfolio(): Promise<Record<string, unknown>> {
  return apiFetch("/portfolio/sync", { method: "POST" });
}

export async function fetchPortfolioHistory(date: string): Promise<{
  date: string;
  snapshot: { total_usd: number; holdings: Array<Record<string, unknown>> } | null;
}> {
  return apiFetch(`/portfolio/history/${date}`);
}

export async function fetchPortfolioHeatmap(): Promise<{
  rows: Array<{ asset: string; return_pct: number; volatility_pct: number }>;
}> {
  return apiFetch("/portfolio/heatmap");
}

export type InboxItemPayload = {
  id: number;
  category: string;
  title: string;
  body: string;
  created_at: string;
  read: boolean;
};

export async function fetchStrategies(): Promise<{
  strategies: Array<{ id: string; description: string; kind: string; timeframes: string[] }>;
}> {
  return apiFetch("/strategies");
}

export async function exportStrategyTemplate(strategyId: string): Promise<{ json: string }> {
  return apiFetch(`/strategies/${strategyId}/export`);
}

export async function importStrategyTemplate(json: string): Promise<{ strategy_id: string }> {
  return apiFetch("/strategies/import", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ json }),
  });
}

export async function fetchBacktestLibrary(): Promise<{
  runs: Array<{ id: number; strategy: string; pair: string; tag: string | null; created_at: string }>;
}> {
  return apiFetch("/backtest/library");
}

export async function cloneBacktestRun(
  runId: number,
  tag?: string,
): Promise<{ id: number }> {
  return apiFetch(`/backtest/library/${runId}/clone`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ tag }),
  });
}

export async function compareBacktestRuns(runIds: number[]): Promise<Record<string, unknown>> {
  return apiFetch("/backtest/compare", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ run_ids: runIds }),
  });
}

export async function addBot(body: {
  label: string;
  strategy_id: string;
  pair: string;
  equity_usd?: number;
}): Promise<void> {
  await apiFetch("/bots", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}

export async function triggerHyperopt(strategy: string, pair: string): Promise<Record<string, unknown>> {
  return apiFetch("/hyperopt", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ strategy, pair, epochs: 50 }),
  });
}

export async function fetchExportHub(): Promise<{
  exports: Array<{ id: string; path: string; format: string }>;
}> {
  return apiFetch("/export/hub");
}

export async function fetchResearchCorrelation(): Promise<{
  correlation: { assets: string[]; matrix: number[][] };
  suggestions: string[];
}> {
  return apiFetch("/research/correlation");
}

export async function runWalkForward(): Promise<Record<string, unknown>> {
  return apiFetch("/research/walk-forward", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ strategy: "multi-tf-example", pair: "BTC/USD" }),
  });
}

export async function runMonteCarloResearch(): Promise<Record<string, unknown>> {
  return apiFetch("/research/monte-carlo", { method: "POST" });
}

export async function runPortfolioMonteCarlo(): Promise<Record<string, unknown>> {
  return apiFetch("/research/portfolio-monte-carlo", { method: "POST" });
}

export async function fetchHyperoptHeatmap(): Promise<Record<string, unknown>> {
  return apiFetch("/research/hyperopt-heatmap");
}

export async function fetchExitRules(): Promise<Record<string, unknown>> {
  return apiFetch("/strategies/exit-rules");
}

export async function saveExitRules(rules: Record<string, unknown>): Promise<void> {
  await apiFetch("/strategies/exit-rules", {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(rules),
  });
}

export async function fetchBillingDashboard(): Promise<Record<string, unknown>> {
  return apiFetch("/billing/dashboard");
}

export async function enrollBilling(termsVersion: string, ratePct = 0.12): Promise<Record<string, unknown>> {
  return apiFetch("/billing/enroll", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ license_rate_pct: ratePct, terms_version: termsVersion, accept_terms: true }),
  });
}

export async function processBillingTrades(): Promise<Record<string, unknown>> {
  return apiFetch("/billing/process-trades", { method: "POST" });
}

export async function fetchBillingSettlement(period?: string): Promise<Record<string, unknown>> {
  const q = period ? `?period=${encodeURIComponent(period)}` : "";
  return apiFetch(`/billing/settlement${q}`);
}

export async function markBillingPaid(): Promise<Record<string, unknown>> {
  return apiFetch("/billing/mark-paid", { method: "POST" });
}

export async function createBillingLightningInvoice(
  period: string,
  amountUsd: number,
): Promise<Record<string, unknown>> {
  return apiFetch("/billing/lightning-invoice", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ period, amount_usd: amountUsd }),
  });
}

export async function createBillingLightningInvoice(
  period: string,
  amountUsd: number,
): Promise<Record<string, unknown>> {
  return apiFetch("/billing/lightning-invoice", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ period, amount_usd: amountUsd }),
  });
}

export async function fetchAiRecommendations(): Promise<{
  recommendations: Array<Record<string, unknown>>;
  disclaimer: string;
}> {
  return apiFetch("/ai/recommendations");
}

export async function fetchCuratedLibrary(): Promise<{
  version: string;
  presets: Array<Record<string, unknown>>;
}> {
  return apiFetch("/ai/curated-library");
}

export async function fetchGrowthReferral(): Promise<{ code: string }> {
  return apiFetch("/growth/referral");
}

export async function fetchGrowthLeaderboard(): Promise<{
  rows: Array<{ pseudonym: string; score_usd: number }>;
}> {
  return apiFetch("/growth/leaderboard");
}

export async function optInLeaderboard(scoreUsd: number): Promise<Record<string, unknown>> {
  return apiFetch("/growth/leaderboard/opt-in", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ score_usd: scoreUsd }),
  });
}

export async function enableBoostMode(): Promise<Record<string, unknown>> {
  return apiFetch("/billing/boost-mode", { method: "POST" });
}

export async function fetchPlatformForager(): Promise<{
  pair_count: number;
  pairs: Array<Record<string, unknown>>;
}> {
  return apiFetch("/platform/forager");
}

export async function fetchPlatformFunding(): Promise<{
  rows: Array<Record<string, unknown>>;
}> {
  return apiFetch("/platform/funding");
}

export async function fetchPlatformPostgres(): Promise<Record<string, unknown>> {
  return apiFetch("/platform/postgres/status");
}

export async function syncOnchainWallet(address: string): Promise<Record<string, unknown>> {
  return apiFetch("/platform/onchain/sync", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ address }),
  });
}

export async function draftNlStrategy(text: string): Promise<Record<string, unknown>> {
  return apiFetch("/ai/nl-draft", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text }),
  });
}

export async function fetchNotificationInbox(): Promise<{ items: InboxItemPayload[] }> {
  return apiFetch("/notifications/inbox");
}

export function connectLiveSocket(
  onMessage: (data: Record<string, unknown>) => void,
): WebSocket | null {
  if (typeof WebSocket === "undefined") return null;
  const proto = window.location.protocol === "https:" ? "wss" : "ws";
  const host = window.location.host;
  const ws = new WebSocket(`${proto}://${host}${API_BASE}/ws/live`);
  ws.onmessage = (ev) => {
    try {
      onMessage(JSON.parse(String(ev.data)) as Record<string, unknown>);
    } catch {
      /* ignore malformed frames */
    }
  };
  return ws;
}
