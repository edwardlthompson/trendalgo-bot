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
    timeframe?: string;
    equity_mode?: "base" | "quote" | "portfolio_pct" | "usd" | "pct" | "manual";
    equity_input?: number;
    ta_params?: Record<string, number>;
    pnl_usd?: number;
    pnl_pct?: number;
    realized_pnl_usd?: number;
    unrealized_pnl_usd?: number;
    trade_count?: number;
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
    let detail = `API ${resp.status}`;
    try {
      const body = (await resp.json()) as { detail?: string | Array<{ msg?: string }> };
      if (typeof body.detail === "string") detail = body.detail;
      else if (Array.isArray(body.detail) && body.detail[0]?.msg) detail = body.detail[0].msg;
    } catch {
      /* keep status-only message */
    }
    throw new Error(detail);
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

export type ExchangeFeeSchedule = {
  exchange_id: string;
  taker_pct: number;
  maker_pct: number;
  tier: string;
  source_url: string;
};

export type FleetTestStatus = {
  strategy_id: string;
  timeframe: string;
  status: string;
  net_profit?: number | null;
  trades?: number;
  phase?: string;
};

export type FleetActiveSnapshot = {
  id?: string;
  status: "idle" | "running" | "complete" | "error";
  phase?: "pass1" | "optimize_params" | "optimize_tsl" | "complete";
  exchange_id?: string;
  pair?: string;
  stake_usd?: number;
  trailing_stop_pct?: number;
  lookback_days?: number;
  lookback_seconds?: number;
  total_combinations?: number;
  completed?: number;
  progress_pct?: number;
  elapsed_seconds?: number;
  current_timeframe?: string;
  current_strategy?: string;
  current_test?: string;
  eta_seconds?: number | null;
  messages?: string[];
  recent_tests?: FleetTestStatus[];
  top10?: FleetResultRow[];
  summary?: Record<string, unknown>;
  error?: string | null;
};

export type FleetResultRow = {
  rank?: number;
  strategy_id: string;
  timeframe: string;
  net_profit: number;
  gross_profit: number;
  fees_paid: number;
  trades: number;
  tsl_hits?: number;
  bar_count: number;
  lookback_seconds?: number;
  win_rate?: number;
  fee_taker_pct?: number;
  trailing_stop_pct?: number;
  params?: Record<string, number | string | boolean>;
  phase?: string;
  optimized?: boolean;
  optimal_tsl_pct?: number;
  tsl_optimized?: boolean;
  baseline_net_profit?: number;
};

export type FleetLatestPayload = {
  job_id?: string;
  exchange_id?: string;
  pair?: string;
  stake_usd?: number;
  created_at?: string;
  summary?: Record<string, unknown>;
  rankings: FleetResultRow[];
  total_rankings: number;
  limit?: number;
  offset?: number;
};

export async function fetchExchangeFees(): Promise<{
  tier: string;
  exchanges: ExchangeFeeSchedule[];
}> {
  return apiFetch("/backtest/exchange-fees");
}

export type FleetHistoryEntry = {
  job_id: string;
  exchange_id: string;
  pair: string;
  stake_usd: number;
  created_at: string;
  lookback_days?: number;
  timeframes_tested?: string[];
  top10_count?: number;
  best_strategy?: string;
  best_net_profit?: number;
  best_timeframe?: string;
  buy_hold_net?: number;
};

export async function startFleetBacktest(body: {
  exchange_id: string;
  pair: string;
  stake_usd?: number;
}): Promise<FleetActiveSnapshot> {
  return apiFetch<FleetActiveSnapshot>("/backtest/fleet", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}

export async function fetchFleetActive(): Promise<FleetActiveSnapshot> {
  return apiFetch<FleetActiveSnapshot>("/backtest/fleet/active");
}

export async function fetchFleetLatest(opts?: {
  limit?: number;
  offset?: number;
  group_by?: string;
}): Promise<FleetLatestPayload> {
  const params = new URLSearchParams();
  if (opts?.limit != null) params.set("limit", String(opts.limit));
  if (opts?.offset != null) params.set("offset", String(opts.offset));
  if (opts?.group_by) params.set("group_by", opts.group_by);
  const qs = params.toString();
  return apiFetch<FleetLatestPayload>(`/backtest/fleet/latest${qs ? `?${qs}` : ""}`);
}

export async function fetchFleetHistory(limit = 20): Promise<{
  runs: FleetHistoryEntry[];
  total: number;
}> {
  return apiFetch(`/backtest/fleet/history?limit=${limit}`);
}

export async function fetchFleetHistoryRun(jobId: string): Promise<FleetLatestPayload & {
  final_top10?: FleetResultRow[];
}> {
  return apiFetch(`/backtest/fleet/history/${encodeURIComponent(jobId)}`);
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

export type PortfolioPerformanceRange = "1y" | "6m" | "3m" | "1m" | "14d" | "7d" | "24h";

export type PortfolioPerformancePayload = {
  range: string;
  points: Array<{ time: number; value: number }>;
  top10_index: Array<{ time: number; value: number }>;
  comparison: {
    portfolio_return_pct: number;
    top10_return_pct: number;
    alpha_pct: number;
    symbols?: string[];
  };
  top10_symbols?: string[];
  asset?: string;
  quantity?: number;
};

export async function fetchPortfolioPerformance(
  range: PortfolioPerformanceRange,
): Promise<PortfolioPerformancePayload> {
  return apiFetch(`/portfolio/performance?range=${encodeURIComponent(range)}`);
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

export type PortfolioGoalPayload = {
  target_net_worth_usd: number;
  label: string;
  deadline?: string | null;
  goal_type?: string;
  horizon_months?: number;
  target_return_pct?: number;
};

export async function updatePortfolioGoal(body: PortfolioGoalPayload): Promise<{ goal: Record<string, unknown> }> {
  return apiFetch("/portfolio/goals", {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
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

export async function fetchBotLimits(): Promise<{
  max_bots_total: number;
  max_enabled_bots: number;
  max_sub_minute_enabled: number;
  max_1s_enabled: number;
  sub_minute_intervals: string[];
  bot_count: number;
  enabled_count: number;
  paper: boolean;
  ohlcv_cache?: {
    bot_scoped: boolean;
    dedupe_shared_pair_timeframe: boolean;
    limits_adjustment: string;
    reason: string;
  };
  ta_cache?: {
    shared_fingerprint: boolean;
    incremental_tail: boolean;
    limits_adjustment: string;
    reason: string;
  };
}> {
  return apiFetch("/bots/limits");
}

export type OhlcvWarmupJob = {
  id?: string;
  status: "idle" | "running" | "complete" | "error";
  progress_pct?: number;
  total_series?: number;
  completed_series?: number;
  current_series?: string;
  bars_cached?: number;
  bars_downloaded?: number;
  messages?: string[];
  series_results?: Array<{
    pair: string;
    timeframe: string;
    bars: number;
    downloaded: number;
    bots: string[];
  }>;
  error?: string | null;
};

export async function startOhlcvWarmup(): Promise<OhlcvWarmupJob> {
  return apiFetch("/bots/ohlcv/warmup", { method: "POST" });
}

export async function fetchOhlcvWarmupActive(): Promise<OhlcvWarmupJob> {
  return apiFetch("/bots/ohlcv/warmup/active");
}

export async function fetchOhlcvCacheStatus(): Promise<{
  bot_scoped: boolean;
  bot_count: number;
  unique_series: number;
  series: Array<{
    pair: string;
    timeframe: string;
    cached_bars: number;
    expected_bars: number;
    coverage_pct: number;
    bots: string[];
  }>;
}> {
  return apiFetch("/bots/ohlcv/cache");
}

export async function addBot(body: {
  label: string;
  strategy_id?: string;
  pair?: string;
  equity_usd?: number;
  exchange?: string;
  timeframe?: string;
  enabled?: boolean;
  ta_params?: Record<string, number>;
}): Promise<{ id: number; bots: DashboardData["bots"] }> {
  return apiFetch("/bots", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}

export async function setBotEnabled(
  botId: number,
  enabled: boolean,
): Promise<{ bots: DashboardData["bots"] }> {
  return apiFetch(`/bots/${botId}/enabled`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ enabled }),
  });
}

export async function updateBot(
  botId: number,
  body: {
    label: string;
    strategy_id: string;
    pair: string;
    exchange?: string;
    equity_usd: number;
    equity_mode?: "base" | "quote" | "portfolio_pct" | "usd" | "pct" | "manual";
    equity_input?: number;
    timeframe?: string;
    ta_params?: Record<string, number>;
  },
): Promise<{ bots: DashboardData["bots"] }> {
  return apiFetch(`/bots/${botId}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}

export type BacktestRanking = {
  id?: string;
  fn?: string;
  indicator?: string;
  ta_function?: string;
  strategy_id?: string;
  profit_total?: number;
  trades?: number;
  timeframe?: string;
  pair?: string;
  exchange_id?: string;
};

export type TaLibraryItem = { id: string; name: string; category: string };
export type TaLibraryCategory = { name: string; items: TaLibraryItem[] };

export type BotEquityLimits = {
  base: { symbol: string; max: number };
  quote: { symbol: string; max: number };
  portfolio_usd: number;
  paper?: boolean;
};

export type OhlcvBar = {
  time: number;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
};

export type TradeHighlightRegion = {
  time_start: number;
  time_end: number;
  entry_price: number;
  exit_price: number;
  profitable: boolean;
  pnl_usd?: number | null;
};

export type BotDetailData = {
  bot: NonNullable<DashboardData["bots"]>[number] & {
    equity_mode?: string;
    equity_input?: number;
    ta_params?: Record<string, number>;
  };
  realized_pnl_usd: number;
  unrealized_pnl_usd: number;
  pnl_usd: number;
  pnl_pct: number;
  trade_count: number;
  trades: Array<{
    pair: string;
    side: string;
    stake_usd: number;
    pnl_usd: number;
    created_at: string;
  }>;
  simulated_trades?: Array<{
    pair: string;
    side: string;
    stake_usd: number;
    pnl_usd: number;
    created_at: string;
    simulated?: boolean;
  }>;
  chart: Array<{ time: number; value: number }>;
  ohlcv?: OhlcvBar[];
  trade_markers?: Array<{ time: number; side: string; pnl_usd?: number | null; pnl_pct?: number | null }>;
  simulated_markers?: Array<{ time: number; side: string; pnl_usd?: number | null; pnl_pct?: number | null }>;
  trade_regions?: TradeHighlightRegion[];
  simulated_regions?: TradeHighlightRegion[];
  equity_limits?: BotEquityLimits;
  strategy_params: Record<string, number>;
  available_timeframes: string[];
  timeframe_labels?: Record<string, string>;
  param_specs: Array<{ key: string; label?: string; default?: number; min?: number; max?: number }>;
  backtest_top5?: BacktestRanking[];
};

export async function fetchBotDetail(botId: number): Promise<BotDetailData> {
  return apiFetch(`/bots/${botId}`);
}

export async function fetchTaGlossary(): Promise<{
  entries: Array<{ id: string; title: string; short: string; long: string; formula: string }>;
  count: number;
}> {
  return apiFetch("/research/ta-glossary");
}

export async function fetchBotEquityLimits(botId: number): Promise<BotEquityLimits> {
  return apiFetch(`/bots/${botId}/equity-limits`);
}

export async function fetchTaLibrary(): Promise<{ categories: TaLibraryCategory[]; count: number }> {
  return apiFetch("/research/ta-library");
}

export async function fetchExchangePairs(exchangeId: string): Promise<{ pairs: string[] }> {
  return apiFetch(`/exchanges/${encodeURIComponent(exchangeId)}/pairs`);
}

export async function fetchChartTimeframes(): Promise<{
  intervals: string[];
  labels: Record<string, string>;
}> {
  return apiFetch("/constants/timeframes");
}

export async function deleteBot(botId: number): Promise<{ bots: DashboardData["bots"] }> {
  return apiFetch(`/bots/${botId}`, { method: "DELETE" });
}

export async function forceBotTrade(
  botId: number,
  side: "buy" | "sell",
): Promise<Record<string, unknown>> {
  return apiFetch(`/bots/${botId}/force`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ side }),
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

export async function enrollBilling(termsVersion: string, ratePct = 0.05): Promise<Record<string, unknown>> {
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

export async function fetchBillingPaymentAssets(): Promise<{ assets: Array<Record<string, unknown>> }> {
  return apiFetch("/billing/payment/assets");
}

export async function startBillingPayment(period?: string, asset = "BTC"): Promise<Record<string, unknown>> {
  return apiFetch("/billing/payment/start", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ period: period ?? null, asset }),
  });
}

export async function checkBillingPayment(paymentId: string): Promise<Record<string, unknown>> {
  return apiFetch(`/billing/payment/status/${encodeURIComponent(paymentId)}`);
}

export async function markBillingPaid(): Promise<Record<string, unknown>> {
  return apiFetch("/billing/mark-paid", { method: "POST" });
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
