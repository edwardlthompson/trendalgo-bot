import { handleRestartGuard, checkForUpdates } from "./about/aboutSession";
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
  fetchNotificationInbox,
  syncPortfolio,
  addBot,
  cloneBacktestRun,
  compareBacktestRuns,
  exportStrategyTemplate,
  fetchBacktestLibrary,
  fetchStrategies,
  importStrategyTemplate,
  triggerHyperopt,
  fetchExitRules,
  saveExitRules,
  fetchBillingDashboard,
  enrollBilling,
  processBillingTrades,
  fetchBillingSettlement,
  markBillingPaid,
  createBillingLightningInvoice,
  fetchAiRecommendations,
  fetchCuratedLibrary,
  fetchGrowthReferral,
  fetchGrowthLeaderboard,
  fetchPlatformForager,
  fetchPlatformFunding,
  fetchPlatformPostgres,
  fetchExchangeRegistry,
  optInLeaderboard,
  enableBoostMode,
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
  runBacktest,
  runScannerScan,
  saveScannerSettings,
  saveStrategyParams,
  fetchStrategyParams,
  type BacktestPayload,
  type DashboardData,
} from "./api/client";
import { createAppShell, type AppShellState } from "./AppShell";
import type { PortfolioOverviewData } from "./portfolio/PortfolioSections";
import { assetUrl } from "./assetUrl";
import { t } from "./i18n";
import { initTheme, subscribeThemeChange } from "./theme";

function isUpdateAvailableStatus(status: string): boolean {
  return status.startsWith(t("about.update.available"));
}

async function loadPortfolioBundle(): Promise<Partial<AppShellState>> {
  const [overview, heatmap, inbox, rebalance, arbitrage, exchangeRegistry] = await Promise.all([
    fetchPortfolioOverview(),
    fetchPortfolioHeatmap(),
    fetchNotificationInbox(),
    fetchPortfolioRebalance(),
    fetchPortfolioArbitrage(),
    fetchExchangeRegistry(),
  ]);
  return {
    portfolioOverview: {
      net_worth_usd: overview.net_worth_usd,
      daily_pnl_usd: overview.daily_pnl_usd,
      daily_pnl_pct: overview.daily_pnl_pct,
      health_score: overview.health_score,
      max_drawdown_pct: overview.max_drawdown_pct,
      holdings: overview.holdings,
      allocation: overview.allocation,
      pl_breakdown: overview.pl_breakdown,
      periods: overview.periods,
      comparisons: overview.comparisons as PortfolioOverviewData["comparisons"],
      accounts: overview.accounts as PortfolioOverviewData["accounts"],
      performance_goal: overview.performance_goal as PortfolioOverviewData["performance_goal"],
      bot: overview.bot,
    },
    portfolioEquityCurve: overview.equity_curve,
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
  const [pairs, paramsResp, backtest, logs, scannerSnap, scannerSettings, watchlist, portfolio, strategies, library, exportHub, diversification, exitRules, billingDash, aiRecs, curated, referral, leaderboard, forager, funding, postgres] =
    await Promise.all([
      fetchPairs(),
      fetchStrategyParams(dashboard.strategy_id),
      fetchLatestBacktest(),
      fetchDebugLogs(),
      fetchScannerSnapshot(),
      fetchScannerSettings(),
      fetchScannerWatchlist(),
      loadPortfolioBundle(),
      fetchStrategies(),
      fetchBacktestLibrary(),
      fetchExportHub(),
      fetchResearchCorrelation(),
      fetchExitRules(),
      fetchBillingDashboard(),
      fetchAiRecommendations(),
      fetchCuratedLibrary(),
      fetchGrowthReferral(),
      fetchGrowthLeaderboard(),
      fetchPlatformForager(),
      fetchPlatformFunding(),
      fetchPlatformPostgres(),
    ]);
  return {
    dashboard,
    pairs,
    strategyParams: paramsResp.params,
    backtest,
    debugLogs: logs,
    scannerSnapshot: scannerSnap,
    scannerSettings: scannerSettings,
    scannerWatchlist: watchlist,
    strategyTemplates: strategies.strategies,
    backtestLibrary: library.runs,
    exportItems: exportHub.exports,
    diversification: diversification,
    exitRules: {
      trailing_stop_pct: Number(exitRules.trailing_stop_pct ?? 0.03),
      scale_out_pct: Number(exitRules.scale_out_pct ?? 0.5),
      scale_in_enabled: Boolean(exitRules.scale_in_enabled),
      scale_out_enabled: Boolean(exitRules.scale_out_enabled ?? true),
    },
    billingDashboard: billingDash as import("./billing/BillingDashboard").BillingDashboardData,
    billingSettlement: null,
    showBillingSettlement: false,
    aiRecommendations: aiRecs.recommendations as import("./ai/RecommenderPanel").Recommendation[],
    aiDisclaimer: aiRecs.disclaimer,
    curatedPresets: curated.presets as import("./ai/CuratedLibraryPanel").CuratedPreset[],
    curatedVersion: curated.version,
    referralCode: referral.code,
    leaderboardRows: leaderboard.rows,
    portfolioPlatform: { forager, funding, postgres },
    ...portfolio,
    apiOnline: true,
  };
}

export function bootstrapApp(appRoot: HTMLDivElement): void {
  let state: AppShellState = {
    view: "portfolio",
    showAbout: false,
    showSettings: false,
    showInbox: false,
    updateStatus: t("about.update.current"),
    donations: { enabled: false, message: "", links: [] },
    dashboard: null,
    backtest: null,
    backtestLoading: false,
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
    portfolioSnapshotDates: [],
    portfolioHeatmap: [],
    portfolioSelectedDate: null,
    portfolioRebalanceSuggestions: [],
    portfolioArbitrage: { alerts: [], disclaimer: "" },
    portfolioTagFilter: null,
    inboxItems: [],
    strategyTemplates: [],
    composerCode: "# Multi-TF composer\nrsi_entry = 35\nrsi_exit = 65",
    backtestLibrary: [],
    exportItems: [],
    researchResults: {},
    diversification: null,
    exitRules: null,
    billingDashboard: null,
    billingSettlement: null,
    showBillingSettlement: false,
    aiRecommendations: [],
    aiDisclaimer: "",
    curatedPresets: [],
    curatedVersion: "",
    referralCode: "",
    leaderboardRows: [],
    portfolioPlatform: null,
    exchangeRegistry: null,
  };

  async function refreshDashboard(): Promise<void> {
    try {
      const patch = await loadApiData();
      state = { ...state, ...patch };
    } catch {
      state = { ...state, apiOnline: false };
    }
    render();
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
        state = { ...state, ...patch };
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
      onApplyUpdate: () => {
        void handleApplyUpdate();
      },
      canApplyUpdate: isUpdateAvailableStatus(state.updateStatus),
      onRunBacktest: () => {
        const dashboard = state.dashboard;
        if (!dashboard || state.backtestLoading) return;
        state = { ...state, backtestLoading: true };
        render();
        const toggles = document.querySelector("[data-testid='backtest-toggles']");
        const slip = toggles?.querySelector("[data-slippage]") as HTMLInputElement | null;
        const fees = toggles?.querySelector("[data-fees]") as HTMLInputElement | null;
        void runBacktest({
          strategy: dashboard.strategy_id,
          pair: dashboard.pair,
          slippage_pct: slip?.checked ? 0.001 : 0,
          fee_pct: fees?.checked ? 0.001 : 0,
          save_to_library: true,
        })
          .then((backtest: BacktestPayload) => {
            state = { ...state, backtest, backtestLoading: false };
            render();
            void fetchBacktestLibrary().then((lib) => {
              state = { ...state, backtestLibrary: lib.runs };
              render();
            });
          })
          .catch(() => {
            state = { ...state, backtestLoading: false };
            render();
          });
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
          .catch(() => {
            state = { ...state, scannerLoading: false };
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
        void saveScannerSettings(settings).then((saved) => {
          state = { ...state, scannerSettings: saved };
          render();
        });
      },
      onPortfolioSync: () => {
        void syncPortfolio().then(() => refreshDashboard());
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
      onOpenInbox: () => {
        state = { ...state, showInbox: true };
        render();
      },
      onCloseInbox: () => {
        state = { ...state, showInbox: false };
        render();
      },
      onDeployStrategy: (id) => {
        if (!state.dashboard) return;
        void saveStrategyParams(id, state.strategyParams).then(() => {
          state = { ...state, dashboard: { ...state.dashboard!, strategy_id: id } };
          render();
        });
        if (id === "smart-dca" || id === "grid-trading") {
          void addBot({ label: `${id}-bot`, strategy_id: id, pair: state.dashboard.pair });
        }
        void triggerHyperopt(id, state.dashboard.pair);
        refreshDashboard();
      },
      onExportStrategy: (id) => {
        void exportStrategyTemplate(id).then((r) => {
          state = { ...state, composerCode: r.json };
          render();
        });
      },
      onImportStrategy: (json) => {
        void importStrategyTemplate(json).then((r) => refreshDashboard());
      },
      onComposeStrategy: (code) => {
        state = { ...state, composerCode: code };
        render();
      },
      onCloneBacktest: (id) => {
        void cloneBacktestRun(id, `clone-${id}`).then(() =>
          fetchBacktestLibrary().then((lib) => {
            state = { ...state, backtestLibrary: lib.runs };
            render();
          }),
        );
      },
      onCompareBacktests: (ids) => {
        if (ids.length < 2) return;
        void compareBacktestRuns(ids);
      },
      onExportDownload: (path) => {
        window.open(path, "_blank");
      },
      onWalkForward: () => {
        void runWalkForward().then((r) => {
          state = { ...state, researchResults: { walk_forward: r } };
          render();
        });
      },
      onMonteCarlo: () => {
        void runMonteCarloResearch().then((r) => {
          state = { ...state, researchResults: { ...state.researchResults, monte_carlo: r } };
          render();
        });
      },
      onPortfolioMc: () => {
        void runPortfolioMonteCarlo().then((r) => {
          state = { ...state, researchResults: { ...state.researchResults, portfolio_mc: r } };
          render();
        });
      },
      onHeatmap: () => {
        void fetchHyperoptHeatmap().then((r) => {
          state = { ...state, researchResults: { ...state.researchResults, heatmap: r } };
          render();
        });
      },
      onBillingEnroll: () => {
        void enrollBilling("2026-06-draft-1", 0.12).then(() => refreshDashboard());
      },
      onBillingProcess: () => {
        void processBillingTrades().then(() => refreshDashboard());
      },
      onBillingSettlement: () => {
        void fetchBillingSettlement().then((s) => {
          state = {
            ...state,
            billingSettlement: s as import("./billing/pay/SettlementPanel").SettlementData,
            showBillingSettlement: true,
          };
          render();
        });
      },
      onBillingMarkPaid: () => {
        void markBillingPaid().then(() => refreshDashboard());
      },
      onCopySettlement: (text) => {
        void navigator.clipboard?.writeText(text);
      },
      onBillingLightning: () => {
        const period = state.billingDashboard?.current_period ?? "current";
        const amount = state.billingDashboard?.period_rollup.license_fee_usd ?? 0;
        void createBillingLightningInvoice(period, amount);
      },
      onLeaderboardOptIn: () => {
        const score = state.portfolioOverview?.net_worth_usd ?? 0;
        void optInLeaderboard(score).then(() => refreshDashboard());
      },
      onBoostMode: () => {
        void enableBoostMode().then(() => refreshDashboard());
      },
    });
  }

  initTheme();
  subscribeThemeChange(() => render());
  render();
  void refreshDashboard();

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
      navigator.serviceWorker.register(assetUrl("sw.js")).catch(() => {});
    });
  }
}
