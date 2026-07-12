import { handleRestartGuard, checkForUpdates } from "./about/aboutSession";
import { setTaGlossaryEntries, ensureTaGlossaryLoaded } from "./data/taGlossary";
import { glossaryAnchorId } from "./data/glossaryLinkify";
import { ensureTaLibraryBundled } from "./data/taLibraryFallback";
import {
  bundledExchangeFees,
  feeForExchange,
  mergeFeeCatalogs,
} from "./data/exchangeFeesFallback";
import { applyPwaUpdate } from "./about/applyUpdate";
import { loadDonations } from "./about/donations";
import {
  connectLiveSocket,
  fetchDashboard,
  fetchDebugLogs,
  fetchLatestBacktest,
  fetchPairs,
  applyPortfolioRebalance,
  fetchPortfolioArbitrage,
  fetchPortfolioRebalance,
  syncPortfolioAll,
  fetchPortfolioHeatmap,
  fetchPortfolioHistory,
  fetchPortfolioOverview,
  fetchPortfolioPerformance,
  updatePortfolioGoal,
  fetchNotificationInbox,
  deleteBot,
  addBot,
  fetchBotLimits,
  fetchBotDetail,
  forceBotTrade,
  fetchExitRules,
  saveExitRules,
  fetchBillingDashboard,
  enrollBilling,
  processBillingTrades,
  startBillingPayment,
  checkBillingPayment,
  markBillingPaid,
  fetchPlatformForager,
  fetchPlatformFunding,
  fetchPlatformPostgres,
  fetchExchangeRegistry,
  fetchExchangePairs,
  fetchTaLibrary,
  fetchTaGlossary,
  fetchBotEquityLimits,
  fetchExportHub,
  fetchHyperoptHeatmap,
  fetchResearchCorrelation,
  fetchScannerSettings,
  runMonteCarloResearch,
  runPortfolioMonteCarlo,
  runWalkForward,
  fetchScannerSnapshot,
  fetchScannerWatchlist,
  pauseTrading,
  pinScannerPair,
  resumeTrading,
  startFleetBacktest,
  fetchFleetActive,
  fetchFleetLatest,
  fetchFleetHistory,
  fetchFleetHistoryRun,
  fetchExchangeFees,
  runScannerScan,
  saveScannerSettings,
  saveStrategyParams,
  fetchStrategyParams,
  setBotEnabled,
  updateBot,
  fetchAiRecommendations,
  fetchCuratedLibrary,
  fetchGrowthReferral,
  fetchGrowthLeaderboard,
  optInLeaderboard,
  enableBoostMode,
  type BacktestRanking,
  type DashboardData,
  type FleetActiveSnapshot,
  type FleetResultRow,
  type FleetHistoryEntry,
  type ScannerSettingsPayload,
} from "./api/client";
import { createAppShell, type AppShellState } from "./AppShell";
import { showAppToast } from "./shell/shellChrome";
import {
  buildLocalBotDetail,
  isPaperTrading,
  enrichDetailWithPersisted,
  resolveBotDetail,
  type BotDetailContext,
} from "./dashboard/botDetailLocal";
import type { PortfolioOverviewData } from "./portfolio/PortfolioSections";
import { assetUrl } from "./assetUrl";
import { normalizeTimeframe } from "./components/tradingViewIntervals";
import { krakenPairsFallback } from "./data/krakenUsdPairs";
import { t } from "./i18n";
import {
  loadCachedPairs,
  loadCachedTaLibrary,
  saveBotSettings,
  saveCachedPairs,
  saveCachedTaLibrary,
} from "./settings/settingsStore";
import { loadNavigation, saveNavigation } from "./settings/navigationStore";
import { initTheme, subscribeThemeChange } from "./theme";
import { initDisplayCurrency, subscribeDisplayCurrencyChange } from "./settings/displayCurrency";
import { DEFAULT_BOT_LIMITS, checkGuardrailAction, nextBotLabel, syncBotLimits } from "./bots/botGuardrails";
import { showGuardrailNotice } from "./bots/botLimitsBanner";
import {
  deleteBotTemplate,
  getBotTemplate,
  saveBotTemplate,
  templateToNewBotPayload,
} from "./bots/botTemplatesStore";
import { runOhlcvWarmupWithUi } from "./market/ohlcvWarmup";

function isUpdateAvailableStatus(status: string): boolean {
  return status.startsWith(t("about.update.available"));
}

async function loadPortfolioBundle(): Promise<Partial<AppShellState>> {
  const [overview, heatmap, inbox, rebalance, arbitrage, exchangeRegistry, performance] =
    await Promise.all([
    fetchPortfolioOverview(),
    fetchPortfolioHeatmap(),
    fetchNotificationInbox(),
    fetchPortfolioRebalance(),
    fetchPortfolioArbitrage(),
    fetchExchangeRegistry(),
    fetchPortfolioPerformance("1y"),
  ]);
  return {
    portfolioOverview: {
      net_worth_usd: overview.net_worth_usd,
      daily_pnl_usd: overview.daily_pnl_usd,
      daily_pnl_pct: overview.daily_pnl_pct,
      health_score: overview.health_score,
      max_drawdown_pct: overview.max_drawdown_pct,
      holdings: overview.holdings as PortfolioOverviewData["holdings"],
      allocation: overview.allocation,
      pl_breakdown: overview.pl_breakdown,
      periods: overview.periods,
      comparisons: overview.comparisons as PortfolioOverviewData["comparisons"],
      accounts: overview.accounts as PortfolioOverviewData["accounts"],
      performance_goal: overview.performance_goal as PortfolioOverviewData["performance_goal"],
      bot: overview.bot,
    },
    portfolioEquityCurve: performance.points,
    portfolioTop10Curve: performance.top10_index,
    portfolioTop10Comparison: performance.comparison,
    portfolioPerformanceRange: "1y",
    portfolioSnapshotDates: overview.snapshot_dates,
    portfolioHeatmap: heatmap.rows,
    portfolioSelectedDate: overview.snapshot_dates[0] ?? null,
    portfolioRebalanceSuggestions: rebalance.suggestions,
    portfolioArbitrage: arbitrage,
    portfolioTagFilter: null,
    exchangeRegistry: exchangeRegistry.exchanges,
    inboxItems: inbox.items,
  };
}

async function loadApiData(): Promise<Partial<AppShellState>> {
  const dashboard = await fetchDashboard();
  const [pairs, paramsResp, backtest, logs, scannerSnap, scannerSettings, watchlist, portfolio, exportHub, diversification, exitRules, billingDash, forager, funding, postgres, taLibrary, botLimits, fleetLatest, exchangeFees, fleetActive, fleetHistory, aiRecs, curated, referral, leaderboard] =
    await Promise.all([
      fetchPairs(),
      fetchStrategyParams(dashboard.strategy_id),
      fetchLatestBacktest(),
      fetchDebugLogs(),
      fetchScannerSnapshot(),
      fetchScannerSettings(),
      fetchScannerWatchlist(),
      loadPortfolioBundle(),
      fetchExportHub(),
      fetchResearchCorrelation(),
      fetchExitRules(),
      fetchBillingDashboard(),
      fetchPlatformForager(),
      fetchPlatformFunding(),
      fetchPlatformPostgres(),
      fetchTaLibrary().catch(() => ({ categories: loadCachedTaLibrary(), count: 0 })),
      fetchBotLimits().catch(() => DEFAULT_BOT_LIMITS),
      fetchFleetLatest().catch(() => ({ rankings: [], total_rankings: 0 })),
      fetchExchangeFees().catch(() => ({ tier: "retail_default", exchanges: [] })),
      fetchFleetActive().catch(() => ({ status: "idle" as const })),
      fetchFleetHistory().catch(() => ({ runs: [], total: 0 })),
      fetchAiRecommendations().catch(() => ({ recommendations: [], disclaimer: "" })),
      fetchCuratedLibrary().catch(() => ({ version: "1", presets: [] })),
      fetchGrowthReferral().catch(() => ({ code: "" })),
      fetchGrowthLeaderboard().catch(() => ({ rows: [] })),
    ]);
  const taCategories =
    taLibrary.categories.length > 0 ? taLibrary.categories : loadCachedTaLibrary();
  if (taLibrary.categories.length > 0) {
    saveCachedTaLibrary(taLibrary.categories);
  }
  void fetchTaGlossary()
    .then((glossary) => {
      if (glossary.entries?.length) setTaGlossaryEntries(glossary.entries);
    })
    .catch(() => undefined);
  const defaultExchange = "kraken";
  const feeCatalog = mergeFeeCatalogs(exchangeFees.exchanges);
  const krakenFee = feeForExchange(defaultExchange, feeCatalog);
  return {
    dashboard,
    pairs,
    strategyParams: paramsResp.params,
    backtest,
    debugLogs: logs,
    scannerSnapshot: scannerSnap,
    scannerSettings: scannerSettings,
    scannerWatchlist: watchlist,
    exportItems: exportHub.exports,
    diversification: diversification,
    taLibrary: taCategories,
    fleetExchangeId: defaultExchange,
    fleetPair: "BTC/USD",
    fleetStakeUsd: 1000,
    fleetPairs: pairs.length > 2 ? pairs : krakenPairsFallback(),
    fleetActive: fleetActive.status === "idle" ? null : fleetActive,
    fleetResults: fleetLatest.total_rankings > 0 ? fleetLatest : null,
    fleetFeeSchedule: krakenFee,
    fleetFeeCatalog: feeCatalog,
    fleetHistoryRuns: fleetHistory.runs,
    fleetSelectedHistoryJobId: null,
    fleetFilterMode: "all" as const,
    fleetFilterTimeframe: "60",
    backtestLoading: fleetActive.status === "running",
    botExchangePairs: pairs.length > 2 ? pairs : krakenPairsFallback(),
    exitRules: {
      trailing_stop_pct: Number(exitRules.trailing_stop_pct ?? 0.03),
      scale_out_pct: Number(exitRules.scale_out_pct ?? 0.5),
      scale_in_enabled: Boolean(exitRules.scale_in_enabled),
      scale_out_enabled: Boolean(exitRules.scale_out_enabled ?? true),
    },
    billingDashboard: billingDash as import("./billing/BillingDashboard").BillingDashboardData,
  billingSettlement: null,
  showBillingSettlement: false,
  billingSettlementAsset: "BTC",
    portfolioPlatform: {
      forager,
      funding,
      postgres: {
        ...postgres,
        experimental: true,
        available: Boolean((postgres as { dual_write_enabled?: boolean }).dual_write_enabled),
        status_note: "experimental",
      },
    },
    botLimits: syncBotLimits(
      botLimits,
      dashboard.bots ?? [],
      dashboard.dry_run ?? botLimits.paper,
    ),
    aiRecommendations: (aiRecs.recommendations ?? []).map((row) => ({
      strategy_id: String(row.strategy_id ?? ""),
      score: Number(row.score ?? 0),
      reasons: Array.isArray(row.reasons) ? row.reasons.map(String) : [],
      requires_backtest: Boolean(row.requires_backtest),
    })),
    aiDisclaimer: aiRecs.disclaimer || undefined,
    curatedPresets: (curated.presets ?? []).map((row) => ({
      id: String(row.id ?? row.strategy_id ?? ""),
      label: String(row.label ?? row.strategy_id ?? ""),
      strategy_id: String(row.strategy_id ?? ""),
      version: String(row.version ?? curated.version ?? "1"),
    })),
    curatedVersion: curated.version ?? "1",
    referralCode: referral.code ?? "",
    leaderboard: leaderboard.rows ?? [],
    ...portfolio,
    apiOnline: true,
  };
}

export function bootstrapApp(appRoot: HTMLDivElement): void {
  const initialNav = loadNavigation();
  const initialFeeCatalog = bundledExchangeFees();
  let state: AppShellState = {
    view: initialNav.view,
    showInbox: false,
    updateStatus: t("about.update.current"),
    donations: { enabled: false, message: "", links: [] },
    dashboard: null,
    backtest: null,
    backtestLoading: false,
    fleetExchangeId: "kraken",
    fleetPair: "BTC/USD",
    fleetStakeUsd: 1000,
    fleetPairs: krakenPairsFallback(),
    fleetActive: null,
    fleetResults: null,
    fleetFeeSchedule: feeForExchange("kraken", initialFeeCatalog),
    fleetFeeCatalog: initialFeeCatalog,
    fleetHistoryRuns: [],
    fleetSelectedHistoryJobId: null,
    fleetFilterMode: "all",
    fleetFilterTimeframe: "60",
    strategyParams: {},
    pairs: ["BTC/USD"],
    debugLogs: [],
    apiOnline: false,
    scannerSnapshot: null,
    scannerSettings: null,
    scannerWatchlist: [],
    scannerLoading: false,
    portfolioOverview: null,
    portfolioEquityCurve: [],
    portfolioTop10Curve: [],
    portfolioTop10Comparison: null,
    portfolioPerformanceRange: "1y",
    portfolioSnapshotDates: [],
    portfolioHeatmap: [],
    portfolioSelectedDate: null,
    portfolioRebalanceSuggestions: [],
    portfolioArbitrage: { alerts: [], disclaimer: "" },
    portfolioTagFilter: null,
    inboxItems: [],
    exportItems: [],
    researchResults: {},
    diversification: null,
    exitRules: null,
    billingDashboard: null,
  billingSettlement: null,
  showBillingSettlement: false,
  billingSettlementAsset: "BTC",
    portfolioPlatform: null,
    exchangeRegistry: null,
    selectedBotId: initialNav.selectedBotId,
    botDetail: null,
    botDetailLoading: initialNav.selectedBotId != null && initialNav.view === "dashboard",
    botDetailError: null,
    botDetailLocal: false,
    taLibrary: loadCachedTaLibrary(),
    botExchangePairs: krakenPairsFallback(),
    botLimits: DEFAULT_BOT_LIMITS,
    glossaryReturnView: null,
    glossaryFocusId: null,
    aiRecommendations: null,
    aiDisclaimer: undefined,
    curatedPresets: null,
    curatedVersion: "1",
    referralCode: "",
    leaderboard: null,
  };

  function botDetailContext(): BotDetailContext {
    return {
      dashboard: state.dashboard,
      strategyParams: state.strategyParams,
      taLibrary: state.taLibrary,
    };
  }

  let fleetPoll: ReturnType<typeof setInterval> | null = null;

  function stopFleetPoll(): void {
    if (fleetPoll != null) {
      clearInterval(fleetPoll);
      fleetPoll = null;
    }
  }

  async function reloadFleetResults(): Promise<void> {
    const groupBy =
      state.fleetFilterMode === "strategy"
        ? "strategy"
        : state.fleetFilterMode === "timeframe"
          ? state.fleetFilterTimeframe
          : undefined;
    const latest = await fetchFleetLatest({
      limit: 50,
      group_by: groupBy,
    });
    state = {
      ...state,
      fleetResults: latest.total_rankings > 0 ? latest : state.fleetResults,
    };
    render();
  }

  async function reloadFleetHistory(): Promise<FleetHistoryEntry[]> {
    try {
      const payload = await fetchFleetHistory();
      state = { ...state, fleetHistoryRuns: payload.runs };
      render();
      return payload.runs;
    } catch {
      return state.fleetHistoryRuns;
    }
  }

  async function loadFleetHistoryRun(jobId: string): Promise<void> {
    try {
      const payload = await fetchFleetHistoryRun(jobId);
      state = {
        ...state,
        fleetSelectedHistoryJobId: jobId,
        fleetResults: payload,
        fleetExchangeId: payload.exchange_id ?? state.fleetExchangeId,
        fleetPair: payload.pair ?? state.fleetPair,
        fleetStakeUsd: payload.stake_usd ?? state.fleetStakeUsd,
        fleetActive: null,
        backtestLoading: false,
      };
      render();
    } catch {
      /* keep prior results */
    }
  }

  async function refreshBacktestView(): Promise<void> {
    await reloadFleetHistory();
    await reloadFleetResults();
    const runs = state.fleetHistoryRuns;
    if (runs.length && !state.fleetResults?.rankings?.length) {
      await loadFleetHistoryRun(runs[0].job_id);
      return;
    }
    if (runs.length && !state.fleetSelectedHistoryJobId) {
      await loadFleetHistoryRun(runs[0].job_id);
    }
  }

  function startFleetPoll(): void {
    stopFleetPoll();
    fleetPoll = setInterval(() => {
      void fetchFleetActive().then(async (active: FleetActiveSnapshot) => {
        state = { ...state, fleetActive: active.status === "idle" ? null : active };
        if (active.status === "complete" || active.status === "error") {
          stopFleetPoll();
          state = { ...state, backtestLoading: false };
          await reloadFleetResults();
          await reloadFleetHistory();
        }
        render();
      });
    }, 2000);
  }

  async function createNewBot(fromTemplateId?: string): Promise<void> {
    if (!state.dashboard) return;
    const limits = state.botLimits ?? DEFAULT_BOT_LIMITS;
    const bots = state.dashboard.bots ?? [];
    const label = nextBotLabel(bots);
    let payload = {
      label,
      strategy_id: "RSI",
      pair: state.dashboard.pair ?? "BTC/USD",
      exchange: "kraken",
      timeframe: "60",
      equity_usd: 1000,
      enabled: false,
      ta_params: {} as Record<string, number>,
    };
    if (fromTemplateId) {
      const tpl = getBotTemplate(fromTemplateId);
      if (tpl) payload = templateToNewBotPayload(tpl, label);
    }
    const blocked = checkGuardrailAction(limits, bots, { adding: true });
    if (blocked) {
      showGuardrailNotice(blocked);
      return;
    }
    try {
      const resp = await addBot(payload);
      state = {
        ...state,
        dashboard: { ...state.dashboard, bots: resp.bots },
        botLimits: syncBotLimits(
          limits,
          resp.bots ?? bots,
          state.dashboard?.dry_run ?? limits.paper,
        ),
      };
      render();
      void runOhlcvWarmupWithUi();
      await openBotDetail(resp.id);
    } catch (err) {
      window.alert(String(err instanceof Error ? err.message : err));
    }
  }

  async function createBotFromFleetResult(row: FleetResultRow): Promise<void> {
    if (!state.dashboard) return;
    const limits = state.botLimits ?? DEFAULT_BOT_LIMITS;
    const bots = state.dashboard.bots ?? [];
    const label = nextBotLabel(bots);
    const taParams: Record<string, number> = {};
    if (row.params) {
      for (const [key, value] of Object.entries(row.params)) {
        if (typeof value === "number" && Number.isFinite(value)) taParams[key] = value;
      }
    }
    const payload = {
      label,
      strategy_id: row.strategy_id,
      pair: state.fleetPair,
      exchange: state.fleetExchangeId,
      timeframe: row.timeframe,
      equity_usd: state.fleetStakeUsd,
      enabled: false,
      ta_params: taParams,
    };
    const blocked = checkGuardrailAction(limits, bots, { adding: true });
    if (blocked) {
      showGuardrailNotice(blocked);
      return;
    }
    try {
      const resp = await addBot(payload);
      state = {
        ...state,
        dashboard: { ...state.dashboard, bots: resp.bots },
        botLimits: syncBotLimits(
          limits,
          resp.bots ?? bots,
          state.dashboard?.dry_run ?? limits.paper,
        ),
      };
      render();
      void runOhlcvWarmupWithUi();
      await openBotDetail(resp.id);
    } catch (err) {
      window.alert(String(err instanceof Error ? err.message : err));
    }
  }

  async function loadPairsForExchange(
    exchangeId: string,
    applyPairs?: (pairs: string[]) => void,
  ): Promise<string[]> {
    try {
      const { pairs } = await fetchExchangePairs(exchangeId);
      saveCachedPairs(exchangeId, pairs);
      state = { ...state, botExchangePairs: pairs };
      applyPairs?.(pairs);
      return pairs;
    } catch {
      const fallback =
        loadCachedPairs(exchangeId) ??
        (exchangeId === "kraken" ? krakenPairsFallback() : ["BTC/USD", "ETH/USD"]);
      state = { ...state, botExchangePairs: fallback };
      applyPairs?.(fallback);
      return fallback;
    }
  }

  async function reloadBotDetail(botId: number): Promise<void> {
    const { detail, local } = await resolveBotDetail(botId, botDetailContext(), fetchBotDetail);
    state = { ...state, botDetail: enrichDetailWithPersisted(detail), botDetailLocal: local, botDetailLoading: false, botDetailError: null };
    render();
  }

  function patchLocalBot(botId: number, patch: Record<string, unknown>): void {
    if (!state.dashboard?.bots) return;
    const bots = state.dashboard.bots.map((bot) =>
      bot.id === botId ? { ...bot, ...patch } : bot,
    );
    state = { ...state, dashboard: { ...state.dashboard, bots } };
  }

  function syncNavigationPersist(): void {
    saveNavigation({
      view: state.view,
      selectedBotId: state.selectedBotId,
    });
  }

  async function openBotDetail(botId: number): Promise<void> {
    const bot = state.dashboard?.bots?.find((b) => b.id === botId);
    if (!bot && state.dashboard?.bots) {
      state = {
        ...state,
        selectedBotId: null,
        botDetail: null,
        botDetailLoading: false,
        botDetailError: null,
        botDetailLocal: false,
      };
      syncNavigationPersist();
      render();
      return;
    }
    state = {
      ...state,
      selectedBotId: botId,
      botDetail: null,
      botDetailLoading: true,
      botDetailError: null,
      botDetailLocal: false,
      view: "dashboard",
    };
    syncNavigationPersist();
    render();
    await loadPairsForExchange(String(bot?.exchange ?? "kraken"));
    try {
      const { detail, local } = await resolveBotDetail(botId, botDetailContext(), fetchBotDetail);
      state = {
        ...state,
        botDetail: enrichDetailWithPersisted(detail),
        botDetailLoading: false,
        botDetailError: null,
        botDetailLocal: local,
      };
    } catch {
      state = {
        ...state,
        selectedBotId: null,
        botDetail: null,
        botDetailLoading: false,
        botDetailLocal: false,
        botDetailError: t("bots.detail.load_error"),
      };
      syncNavigationPersist();
    }
    render();
  }

  async function restoreNavigationAfterLoad(): Promise<void> {
    const botId = state.selectedBotId;
    if (botId == null || state.view !== "dashboard" || state.botDetail) return;
    await openBotDetail(botId);
  }

  async function refreshDashboard(): Promise<void> {
    try {
      const patch = await loadApiData();
      state = { ...state, ...patch };
      if ((state.dashboard?.bots?.length ?? 0) > 0) {
        void runOhlcvWarmupWithUi({ silentIfCached: true });
      }
    } catch (err) {
      state = { ...state, apiOnline: false };
      showAppToast(err instanceof Error ? err.message : t("app.status.api_offline"), "error");
    }
    render();
    if (state.view === "billing") {
      void maybeAutoOpenBillingSettlement();
    }
    if (state.backtestLoading && state.fleetActive?.status === "running") {
      startFleetPoll();
    }
    await restoreNavigationAfterLoad();
  }

  function mapPaymentToSettlement(raw: Record<string, unknown>): import("./billing/pay/SettlementPanel").SettlementData {
    return {
      period: String(raw.period ?? ""),
      amount_usd: Number(raw.amount_usd ?? 0),
      address: String(raw.address ?? ""),
      asset: String(raw.asset ?? "BTC"),
      chain: raw.chain != null ? String(raw.chain) : undefined,
      amount_btc: raw.amount_btc != null ? Number(raw.amount_btc) : undefined,
      amount_sats: raw.amount_sats != null ? Number(raw.amount_sats) : undefined,
      amount_to_send: raw.amount_to_send != null ? Number(raw.amount_to_send) : undefined,
      payment_id: raw.id != null ? String(raw.id) : raw.payment_id != null ? String(raw.payment_id) : undefined,
      payment_reference: raw.payment_reference != null ? String(raw.payment_reference) : undefined,
      status: raw.status != null ? String(raw.status) : undefined,
      licensed_until: raw.licensed_until != null ? String(raw.licensed_until) : undefined,
      qr_payload: String(raw.qr_payload ?? ""),
      disclaimer: String(raw.disclaimer ?? ""),
      user_initiated_only: Boolean(raw.user_initiated_only ?? true),
      auto_verify: raw.auto_verify !== false,
      payment_instructions: raw.payment_instructions != null ? String(raw.payment_instructions) : undefined,
      min_confirmations: raw.min_confirmations != null ? Number(raw.min_confirmations) : undefined,
      grace_period_days: raw.grace_period_days != null ? Number(raw.grace_period_days) : undefined,
    };
  }

  async function openBillingSettlement(period?: string, asset?: string): Promise<void> {
    const payAsset = asset ?? state.billingSettlementAsset ?? "BTC";
    try {
      const raw = await startBillingPayment(period, payAsset);
      state = {
        ...state,
        billingSettlement: mapPaymentToSettlement(raw),
        billingSettlementAsset: payAsset,
        showBillingSettlement: true,
      };
      render();
    } catch {
      /* no fee due or API offline */
    }
  }

  async function maybeAutoOpenBillingSettlement(): Promise<void> {
    const dash = state.billingDashboard;
    if (!dash || state.showBillingSettlement) return;
    const fee = dash.period_rollup.license_fee_usd;
    if (fee <= 0) return;
    const status = dash.license_status;
    const graceDay = Number(status.grace_day ?? 0);
    const suspended = Number(status.suspended ?? 0) === 1;
    if (graceDay > 0 || suspended) {
      await openBillingSettlement(dash.current_period);
    }
  }

  async function handleApplyUpdate(): Promise<void> {
    if (!("serviceWorker" in navigator)) return;
    const registration = await navigator.serviceWorker.getRegistration();
    if (!registration) return;
    const applied = await applyPwaUpdate(registration);
    if (applied) {
      state = { ...state, updateStatus: t("about.update.restarting") };
      render();
    }
  }

  function render(): void {
    createAppShell(appRoot, state, {
      onState: (patch) => {
        const prevView = state.view;
        if (patch.view && patch.view !== "dashboard" && patch.view !== "glossary") {
          patch = { ...patch, selectedBotId: null, botDetail: null, botDetailLoading: false, botDetailError: null, botDetailLocal: false };
        }
        state = { ...state, ...patch };
        if (patch.view !== undefined) {
          syncNavigationPersist();
        }
        if (patch.selectedBotId !== undefined) {
          syncNavigationPersist();
        }
        if (patch.view === "backtest" && prevView !== "backtest") {
          void refreshBacktestView();
        }
        if (patch.view === "billing" && prevView !== "billing") {
          void maybeAutoOpenBillingSettlement();
        }
        render();
      },
      onUpdateCheckChange: (enabled) => {
        if (enabled) {
          void checkForUpdates().then((status) => {
            state = { ...state, updateStatus: status };
            render();
          });
        }
      },
      onDisplayCurrencyChange: () => {
        render();
      },
      onApplyUpdate: () => {
        void handleApplyUpdate();
      },
      canApplyUpdate: isUpdateAvailableStatus(state.updateStatus),
      onRunBacktest: () => {
        if (state.backtestLoading) return;
        state = { ...state, backtestLoading: true };
        render();
        void startFleetBacktest({
          exchange_id: state.fleetExchangeId,
          pair: state.fleetPair,
          stake_usd: state.fleetStakeUsd,
        })
          .then((active) => {
            state = { ...state, fleetActive: active };
            render();
            startFleetPoll();
          })
          .catch(() => {
            state = { ...state, backtestLoading: false };
            render();
          });
      },
      onFleetExchangeChange: (exchangeId) => {
        const schedule = feeForExchange(exchangeId, state.fleetFeeCatalog);
        state = {
          ...state,
          fleetExchangeId: exchangeId,
          fleetFeeSchedule: schedule,
        };
        render();
        void fetchExchangeFees()
          .then((payload) => {
            if (!payload.exchanges.length) return;
            const merged = mergeFeeCatalogs(payload.exchanges, state.fleetFeeCatalog);
            const next = feeForExchange(exchangeId, merged);
            state = {
              ...state,
              fleetFeeCatalog: merged,
              fleetFeeSchedule:
                state.fleetExchangeId === exchangeId ? next : state.fleetFeeSchedule,
            };
            render();
          })
          .catch(() => undefined);
        void loadPairsForExchange(exchangeId, (pairs) => {
          state = {
            ...state,
            fleetPairs: pairs,
            fleetPair: pairs.includes(state.fleetPair) ? state.fleetPair : (pairs[0] ?? "BTC/USD"),
          };
          render();
        });
      },
      onFleetPairChange: (pair) => {
        state = { ...state, fleetPair: pair };
        render();
      },
      onFleetStakeChange: (stakeUsd) => {
        state = { ...state, fleetStakeUsd: stakeUsd };
        render();
      },
      onFleetFilterChange: (mode, timeframe) => {
        state = {
          ...state,
          fleetFilterMode: mode,
          fleetFilterTimeframe: timeframe ?? state.fleetFilterTimeframe,
        };
        render();
        void reloadFleetResults();
      },
      onLoadFleetHistoryRun: (jobId) => {
        void loadFleetHistoryRun(jobId);
      },
      onCreateBotFromFleetResult: (row) => {
        void createBotFromFleetResult(row);
      },
      onPause: () => {
        void pauseTrading().then(() => refreshDashboard());
      },
      onResume: () => {
        void resumeTrading().then(() => refreshDashboard());
      },
      onSaveConfig: (params) => {
        if (!state.dashboard) return;
        void saveStrategyParams(state.dashboard.strategy_id, params).then(() =>
          refreshDashboard(),
        );
      },
      onSaveExitRules: (rules) => {
        void saveExitRules(rules).then(() => {
          state = { ...state, exitRules: rules };
          render();
        });
      },
      onRunScanner: () => {
        if (state.scannerLoading) return;
        state = { ...state, scannerLoading: true };
        render();
        void runScannerScan()
          .then((snap) => {
            state = { ...state, scannerSnapshot: snap, scannerLoading: false };
            render();
          })
          .catch((err) => {
            state = { ...state, scannerLoading: false };
            showAppToast(err instanceof Error ? err.message : t("empty.scanner"), "error");
            render();
          });
      },
      onPinPair: (pair) => {
        void pinScannerPair(pair).then((pairs) => {
          state = { ...state, scannerWatchlist: pairs };
          render();
        });
      },
      onSaveScannerSettings: (settings) => {
        void saveScannerSettings(settings as ScannerSettingsPayload).then((saved) => {
          state = { ...state, scannerSettings: saved };
          render();
        });
      },
      onPortfolioSync: () => {
        void syncPortfolioAll().then(() => refreshDashboard());
      },
      onPortfolioSyncAll: () => {
        void syncPortfolioAll().then(() => refreshDashboard());
      },
      onTagFilter: (tag) => {
        state = { ...state, portfolioTagFilter: tag };
        render();
      },
      onRebalanceApply: () => {
        void applyPortfolioRebalance().then(() => refreshDashboard());
      },
      onScrubDate: (date) => {
        void fetchPortfolioHistory(date).then((hist) => {
          if (!hist.snapshot || !state.portfolioOverview) return;
          state = {
            ...state,
            portfolioSelectedDate: date,
            portfolioOverview: {
              ...state.portfolioOverview,
              net_worth_usd: Number(hist.snapshot.total_usd),
              holdings: hist.snapshot.holdings as Array<Record<string, number | string>>,
            },
          };
          render();
        });
      },
      onPerformanceRangeChange: (range) => {
        void fetchPortfolioPerformance(range).then((payload) => {
          state = {
            ...state,
            portfolioPerformanceRange: range,
            portfolioEquityCurve: payload.points,
            portfolioTop10Curve: payload.top10_index,
            portfolioTop10Comparison: payload.comparison,
          };
          render();
        });
      },
      onSaveGoal: (payload) => {
        void updatePortfolioGoal({
          target_net_worth_usd: payload.target_net_worth_usd,
          label: payload.label,
          goal_type: payload.goal_type,
          horizon_months: payload.horizon_months,
          target_return_pct: payload.target_return_pct,
        }).then(() => refreshDashboard());
      },
      onBotToggle: (botId, enabled) => {
        const limits = state.botLimits ?? DEFAULT_BOT_LIMITS;
        const bots = state.dashboard?.bots ?? [];
        const bot = bots.find((b) => b.id === botId);
        if (enabled && bot) {
          const blocked = checkGuardrailAction(limits, bots, {
            enabling: true,
            timeframe: String(bot.timeframe ?? "60"),
            botId,
          });
          if (blocked) {
            showGuardrailNotice(blocked);
            return;
          }
        }
        void setBotEnabled(botId, enabled)
          .then((resp) => {
            if (state.dashboard) {
              state = {
                ...state,
                dashboard: { ...state.dashboard, bots: resp.bots },
                botLimits: resp.bots
                  ? syncBotLimits(limits, resp.bots, state.dashboard?.dry_run ?? limits.paper)
                  : state.botLimits,
              };
            }
            if (enabled) {
              void runOhlcvWarmupWithUi();
            }
            void refreshDashboard();
          })
          .catch((err) => {
            const msg = err instanceof Error ? err.message : String(err);
            window.alert(`${t("bots.limits.blocked_title")}\n\n${msg}`);
          });
      },
      onCreateBot: () => {
        void createNewBot();
      },
      onApplyTemplate: (templateId) => {
        void createNewBot(templateId);
      },
      onDeleteTemplate: (templateId) => {
        deleteBotTemplate(templateId);
        render();
      },
      onSaveBotTemplate: (botId, name) => {
        const detail = state.botDetail;
        const bot = detail?.bot.id === botId ? detail.bot : state.dashboard?.bots?.find((b) => b.id === botId);
        if (!bot) return;
        try {
          saveBotTemplate(
            name,
            {
              label: bot.label,
              strategy_id: bot.strategy_id,
              pair: bot.pair,
              exchange: String(bot.exchange ?? "kraken"),
              timeframe: normalizeTimeframe(String(bot.timeframe ?? "60")),
              equity_mode: (bot.equity_mode as "quote") ?? "quote",
              equity_input: Number(bot.equity_input ?? bot.equity_usd),
              ta_params: detail?.strategy_params ?? {},
            },
            botId,
          );
          window.alert(t("bots.templates.saved"));
          render();
        } catch (err) {
          window.alert(String(err instanceof Error ? err.message : err));
        }
      },
      onBotUpdate: (botId, payload) => {
        const limits = state.botLimits ?? DEFAULT_BOT_LIMITS;
        const bots = state.dashboard?.bots ?? [];
        const existing = bots.find((b) => b.id === botId);
        const willRun = existing?.enabled ?? state.botDetail?.bot.enabled ?? false;
        if (willRun) {
          const blocked = checkGuardrailAction(limits, bots, {
            enabling: true,
            timeframe: payload.timeframe,
            botId,
          });
          if (blocked) {
            showGuardrailNotice(blocked);
            return;
          }
        }
        saveBotSettings(botId, {
          label: payload.label,
          strategy_id: payload.strategy_id,
          pair: payload.pair,
          exchange: payload.exchange,
          timeframe: payload.timeframe,
          equity_mode: payload.equity_mode,
          equity_input: payload.equity_input,
          ta_params: payload.ta_params,
        });
        if (isPaperTrading(botDetailContext())) {
          patchLocalBot(botId, payload);
          const detail = buildLocalBotDetail(botId, botDetailContext());
          state = { ...state, botDetail: detail, botDetailLocal: true };
          render();
          return;
        }
        void updateBot(botId, payload)
          .then(() => reloadBotDetail(botId))
          .catch((err) => {
            const msg = err instanceof Error ? err.message : String(err);
            window.alert(`${t("bots.limits.blocked_title")}\n\n${msg}`);
          });
      },
      onBotDelete: (botId) => {
        void deleteBot(botId).then(() => {
          if (state.selectedBotId === botId) {
            state = { ...state, selectedBotId: null, botDetail: null };
            syncNavigationPersist();
          }
          void refreshDashboard();
        });
      },
      onBotForceTrade: (botId, side) => {
        if (isPaperTrading(botDetailContext())) {
          const bot = state.dashboard?.bots?.find((row) => row.id === botId);
          if (!bot || !state.botDetail) return;
          const trade = {
            pair: bot.pair,
            side,
            stake_usd: Math.round(bot.equity_usd * 0.05),
            pnl_usd: side === "sell" ? 4.5 : 0,
            created_at: new Date().toISOString(),
          };
          state = {
            ...state,
            botDetail: {
              ...state.botDetail,
              trades: [...state.botDetail.trades, trade],
              trade_count: state.botDetail.trade_count + 1,
            },
            botDetailLocal: true,
          };
          render();
          return;
        }
        void forceBotTrade(botId, side).then(() => reloadBotDetail(botId));
      },
      onOpenBot: (botId) => {
        void openBotDetail(botId);
      },
      onCloseBot: () => {
        state = {
          ...state,
          selectedBotId: null,
          botDetail: null,
          botDetailLoading: false,
          botDetailError: null,
          botDetailLocal: false,
        };
        syncNavigationPersist();
        render();
      },
      onBotSaveParams: (botId, strategyId, params) => {
        const bot = state.botDetail?.bot;
        if (bot) {
          saveBotSettings(botId, {
            label: bot.label,
            strategy_id: strategyId,
            pair: bot.pair,
            exchange: String(bot.exchange ?? "kraken"),
            timeframe: normalizeTimeframe(String(bot.timeframe ?? "60")),
            equity_mode: (bot.equity_mode as "quote") ?? "quote",
            equity_input: Number(bot.equity_input ?? bot.equity_usd),
            ta_params: params,
          });
        }
        if (isPaperTrading(botDetailContext())) {
          patchLocalBot(botId, { ta_params: params });
          state = { ...state, strategyParams: params };
          const detail = buildLocalBotDetail(botId, botDetailContext());
          state = { ...state, botDetail: { ...detail, strategy_params: params }, botDetailLocal: true };
          render();
          return;
        }
        void updateBot(botId, {
          label: state.botDetail?.bot.label ?? "",
          strategy_id: strategyId,
          pair: state.botDetail?.bot.pair ?? "BTC/USD",
          exchange: state.botDetail?.bot.exchange ?? "kraken",
          equity_usd: state.botDetail?.bot.equity_usd ?? 1000,
          equity_mode: (state.botDetail?.bot.equity_mode as "quote") ?? "quote",
          equity_input: state.botDetail?.bot.equity_input,
          timeframe: state.botDetail?.bot.timeframe ?? "60",
          ta_params: params,
        }).then(() => reloadBotDetail(botId));
      },
      onBotExchangeChange: (exchangeId, applyPairs) => {
        void loadPairsForExchange(exchangeId, applyPairs);
      },
      onOpenGlossary: (strategyId?: string) => {
        const focusId = strategyId?.toUpperCase() ?? null;
        if (focusId) {
          const anchor = glossaryAnchorId(focusId);
          history.replaceState(
            null,
            "",
            `${window.location.pathname}${window.location.search}#${anchor}`,
          );
        }
        const returnView = state.view === "glossary" ? state.glossaryReturnView ?? "dashboard" : state.view;
        state = { ...state, view: "glossary", glossaryReturnView: returnView, glossaryFocusId: focusId };
        render();
      },
      onCloseGlossary: () => {
        state = {
          ...state,
          view: state.glossaryReturnView ?? "dashboard",
          glossaryReturnView: null,
          glossaryFocusId: null,
        };
        history.replaceState(null, "", window.location.pathname + window.location.search);
        render();
      },
      onBotPairChange: (botId, pair) => {
        const base = pair.split("/")[0]?.toUpperCase() ?? "BTC";
        const quote = pair.split("/")[1]?.toUpperCase() ?? "USD";
        if (isPaperTrading(botDetailContext())) {
          const detail = state.botDetail;
          if (!detail || detail.bot.id !== botId) return;
          state = {
            ...state,
            botDetail: {
              ...detail,
              equity_limits: {
                base: { symbol: base, max: 10 },
                quote: { symbol: quote, max: 50_000 },
                portfolio_usd: 100_000,
                paper: true,
              },
            },
          };
          render();
          return;
        }
        void fetchBotEquityLimits(botId).then((limits) => {
          if (state.botDetail?.bot.id !== botId) return;
          state = { ...state, botDetail: { ...state.botDetail!, equity_limits: limits } };
          render();
        });
      },
      onBotApplyBacktest: (botId, ranking: BacktestRanking) => {
        const bot = state.botDetail?.bot;
        if (!bot) return;
        const strategyId = String(ranking.ta_function ?? ranking.indicator ?? ranking.id ?? bot.strategy_id);
        const payload = {
          label: bot.label,
          strategy_id: strategyId,
          pair: String(ranking.pair ?? bot.pair),
          exchange: String(ranking.exchange_id ?? bot.exchange ?? "kraken"),
          equity_usd: bot.equity_usd,
          equity_mode: (bot.equity_mode as "quote") ?? "quote",
          equity_input: Number(bot.equity_input ?? bot.equity_usd),
          timeframe: String(ranking.timeframe ?? bot.timeframe ?? "60"),
          ta_params: { ...state.botDetail?.strategy_params },
        };
        saveBotSettings(botId, {
          label: payload.label,
          strategy_id: payload.strategy_id,
          pair: payload.pair,
          exchange: payload.exchange,
          timeframe: payload.timeframe,
          equity_mode: payload.equity_mode,
          equity_input: payload.equity_input,
          ta_params: payload.ta_params,
        });
        if (isPaperTrading(botDetailContext())) {
          patchLocalBot(botId, payload);
          const detail = buildLocalBotDetail(botId, botDetailContext());
          state = { ...state, botDetail: detail, botDetailLocal: true };
          render();
          return;
        }
        void updateBot(botId, payload).then(() => reloadBotDetail(botId));
      },
      onOpenInbox: () => {
        state = { ...state, showInbox: true };
        render();
      },
      onCloseInbox: () => {
        state = { ...state, showInbox: false };
        render();
      },
      onExportDownload: (path) => {
        window.open(path, "_blank");
      },
      onWalkForward: () => {
        state = { ...state, researchResults: { loading: true } };
        render();
        void runWalkForward()
          .then((r) => {
            state = { ...state, researchResults: { walk_forward: r } };
            render();
          })
          .catch((err) => {
            state = { ...state, researchResults: { error: String(err) } };
            showAppToast(String(err), "error");
            render();
          });
      },
      onMonteCarlo: () => {
        state = { ...state, researchResults: { loading: true } };
        render();
        void runMonteCarloResearch()
          .then((r) => {
            state = { ...state, researchResults: { ...state.researchResults, loading: false, monte_carlo: r } };
            render();
          })
          .catch((err) => {
            state = { ...state, researchResults: { error: String(err) } };
            showAppToast(String(err), "error");
            render();
          });
      },
      onPortfolioMc: () => {
        state = { ...state, researchResults: { loading: true } };
        render();
        void runPortfolioMonteCarlo()
          .then((r) => {
            state = { ...state, researchResults: { ...state.researchResults, loading: false, portfolio_mc: r } };
            render();
          })
          .catch((err) => {
            state = { ...state, researchResults: { error: String(err) } };
            showAppToast(String(err), "error");
            render();
          });
      },
      onHeatmap: () => {
        state = { ...state, researchResults: { loading: true } };
        render();
        void fetchHyperoptHeatmap()
          .then((r) => {
            state = { ...state, researchResults: { heatmap: r } };
            render();
          })
          .catch((err) => {
            state = { ...state, researchResults: { error: String(err) } };
            showAppToast(String(err), "error");
            render();
          });
      },
      onBillingEnroll: () => {
        void enrollBilling("2026-06-draft-1", 0.05).then(() => refreshDashboard());
      },
      onBillingProcess: () => {
        void processBillingTrades().then(() => refreshDashboard());
      },
      onBillingSettlement: () => {
        void openBillingSettlement(state.billingDashboard?.current_period);
      },
      onBillingAssetChange: (asset) => {
        void openBillingSettlement(state.billingDashboard?.current_period, asset);
      },
      onBillingMarkPaid: () => {
        void markBillingPaid().then(() => refreshDashboard());
      },
      onCopySettlement: (text) => {
        void navigator.clipboard?.writeText(text);
      },
      onBillingPaymentPoll: async (paymentId) => {
        try {
          const result = await checkBillingPayment(paymentId);
          const payment = (result.payment ?? {}) as Record<string, unknown>;
          const merged = mapPaymentToSettlement({ ...payment, status: result.status ?? payment.status });
          state = { ...state, billingSettlement: merged };
          render();
          return merged;
        } catch {
          return null;
        }
      },
      onBillingPaymentConfirmed: () => {
        void refreshDashboard();
      },
      onDeployStrategy: (strategyId) => {
        state = { ...state, view: "dashboard" };
        render();
        void createNewBot().then(() => {
          showAppToast(t("ai.deployed").replace("{id}", strategyId), "info");
        });
      },
      onGrowthOptIn: () => {
        const score = Number(state.portfolioOverview?.net_worth_usd ?? 0);
        void optInLeaderboard(score)
          .then(() => refreshDashboard())
          .catch((err) => showAppToast(String(err), "error"));
      },
      onGrowthBoost: () => {
        void enableBoostMode()
          .then(() => refreshDashboard())
          .catch((err) => showAppToast(String(err), "error"));
      },
    });
  }

  initTheme();
  initDisplayCurrency();
  subscribeThemeChange(() => render());
  subscribeDisplayCurrencyChange(() => render());
  void Promise.all([ensureTaGlossaryLoaded(), ensureTaLibraryBundled()]).then(() => render());
  render();
  void refreshDashboard().then(() => {
    if (state.view === "backtest") {
      void refreshBacktestView();
    }
  });

  window.addEventListener("trendalgo:nav", ((ev: CustomEvent<string>) => {
    const view = ev.detail as AppShellState["view"];
    if (view) {
      state = { ...state, view, selectedBotId: null, botDetail: null };
      render();
    }
  }) as EventListener);

  window.addEventListener("trendalgo:onboarding-dismiss", () => render());

  const ws = connectLiveSocket((msg) => {
    if (!state.dashboard || msg.type !== "snapshot") return;
    const risk = msg.risk as DashboardData["risk"];
    state = {
      ...state,
      dashboard: {
        ...state.dashboard,
        equity_usd: Number(msg.equity_usd ?? state.dashboard.equity_usd),
        risk,
      },
    };
    render();
  });

  void loadDonations().then((d) => {
    state = { ...state, donations: d };
    render();
  });

  if (!handleRestartGuard()) {
    void checkForUpdates().then((status) => {
      state = { ...state, updateStatus: status };
      render();
    });
  }

  window.addEventListener("online", render);
  window.addEventListener("offline", render);
  window.addEventListener("beforeunload", () => ws?.close());

  if ("serviceWorker" in navigator) {
    window.addEventListener("load", () => {
      if (import.meta.env.DEV) {
        void navigator.serviceWorker.getRegistrations().then((regs) =>
          Promise.all(regs.map((reg) => reg.unregister())),
        );
        return;
      }
      navigator.serviceWorker.register(assetUrl("sw.js")).catch(() => {});
    });
  }
}
