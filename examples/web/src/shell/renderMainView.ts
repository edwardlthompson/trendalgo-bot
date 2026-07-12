import { createBacktestPanel } from "../backtest/BacktestPanel";
import type { BacktestPayload, DashboardData } from "../api/client";
import type { ExitRulesState } from "../config/ConfigForm";
import { createBotDashboard, createBotDetailLoading } from "../dashboard/BotDashboard";
import { createBotDetailPage } from "../dashboard/BotDetailPage";
import { createTaGlossaryPage } from "../dashboard/TaGlossaryPage";
import { createDebugLogViewer } from "../debug/DebugLogViewer";
import { createNotificationInbox, type InboxItem } from "../notifications/Inbox";
import { createPortfolioPanel } from "../portfolio/PortfolioPanel";
import type { PortfolioOverviewData } from "../portfolio/PortfolioSections";
import { createScannerPanel } from "../scanner/ScannerPanel";
import type { ScannerSettings, ScannerSnapshot } from "../scanner/ScannerPanel";
import type { PerformanceRange } from "../portfolio/PortfolioPerformanceChart";
import type { EquityPoint } from "../charts/EquityChart";
import { createExportHub, type ExportItem } from "../export/ExportHub";
import { createBillingDashboard, type BillingDashboardData } from "../billing/BillingDashboard";
import { createSettlementPanel, type SettlementData } from "../billing/pay/SettlementPanel";
import { createDiversificationPanel } from "../research/DiversificationPanel";
import { createResearchToolsPanel } from "../research/ResearchTools";
import { createSettingsView } from "../settings/SettingsView";
import type { DonationConfig } from "../about/types";
import type { DisplayCurrencyCode } from "../settings/displayCurrency";
import type { AppView } from "./MobileNav";
import { t } from "../i18n";
import { DEFAULT_BOT_LIMITS, syncBotLimits } from "../bots/botGuardrails";
import { listBotTemplates } from "../bots/botTemplatesStore";
import { createBootSkeleton } from "./shellChrome";
import type { Recommendation } from "../ai/RecommenderPanel";
import type { CuratedPreset } from "../ai/CuratedLibraryPanel";
import { createOnboardingChecklist } from "../onboarding/OnboardingChecklist";

export type MainViewState = {
  view: AppView;
  dashboard: DashboardData | null;
  backtest: BacktestPayload | null;
  backtestLoading: boolean;
  fleetExchangeId: string;
  fleetPair: string;
  fleetStakeUsd: number;
  fleetPairs: string[];
  fleetActive: import("../api/client").FleetActiveSnapshot | null;
  fleetResults: import("../api/client").FleetLatestPayload | null;
  fleetFeeSchedule: import("../api/client").ExchangeFeeSchedule | null;
  fleetHistoryRuns: import("../api/client").FleetHistoryEntry[];
  fleetSelectedHistoryJobId: string | null;
  fleetFilterMode: "all" | "timeframe" | "strategy";
  fleetFilterTimeframe: string;
  strategyParams: Record<string, number>;
  pairs: string[];
  debugLogs: string[];
  scannerSnapshot: ScannerSnapshot | null;
  scannerSettings: ScannerSettings | null;
  scannerWatchlist: string[];
  scannerLoading: boolean;
  portfolioOverview: PortfolioOverviewData | null;
  portfolioEquityCurve: EquityPoint[];
  portfolioTop10Curve: EquityPoint[];
  portfolioTop10Comparison: import("../charts/EquityChart").PerformanceComparison | null;
  portfolioPerformanceRange: PerformanceRange;
  portfolioSnapshotDates: string[];
  portfolioHeatmap: Array<{ asset: string; return_pct: number; volatility_pct: number }>;
  portfolioSelectedDate: string | null;
  portfolioRebalanceSuggestions: Array<Record<string, unknown>>;
  portfolioArbitrage: { alerts: Array<Record<string, unknown>>; disclaimer: string };
  portfolioTagFilter: string | null;
  showInbox: boolean;
  inboxItems: InboxItem[];
  exportItems: ExportItem[];
  researchResults: Record<string, unknown>;
  diversification: { suggestions: string[]; correlation: { assets: string[]; matrix: number[][] } } | null;
  exitRules: ExitRulesState | null;
  billingDashboard: BillingDashboardData | null;
  billingSettlement: SettlementData | null;
  showBillingSettlement: boolean;
  billingSettlementAsset?: string;
  portfolioPlatform: import("../platform/PlatformPanel").PlatformData | null;
  exchangeRegistry: import("../portfolio/AccountsPanel").ExchangeRegistryEntry[] | null;
  selectedBotId: number | null;
  botDetail: import("../api/client").BotDetailData | null;
  botDetailLoading: boolean;
  botDetailLocal: boolean;
  taLibrary: import("../api/client").TaLibraryCategory[];
  botExchangePairs: string[];
  botLimits: import("../bots/botGuardrails").BotLimits | null;
  glossaryFocusId: string | null;
  updateStatus: string;
  donations: DonationConfig;
  canApplyUpdate?: boolean;
  aiRecommendations?: Recommendation[] | null;
  aiDisclaimer?: string;
  curatedPresets?: CuratedPreset[] | null;
  curatedVersion?: string;
  referralCode?: string;
  leaderboard?: Array<{ pseudonym: string; score_usd: number }> | null;
};

export type MainViewCallbacks = {
  onRunBacktest: () => void;
  onFleetExchangeChange: (exchangeId: string) => void;
  onFleetPairChange: (pair: string) => void;
  onFleetStakeChange: (stakeUsd: number) => void;
  onFleetFilterChange: (mode: "all" | "timeframe" | "strategy", timeframe?: string) => void;
  onLoadFleetHistoryRun: (jobId: string) => void;
  onCreateBotFromFleetResult: (row: import("../api/client").FleetResultRow) => void;
  onPause: () => void;
  onResume: () => void;
  onSaveConfig: (params: Record<string, number>) => void;
  onSaveExitRules?: (rules: ExitRulesState) => void;
  onRunScanner: () => void;
  onPinPair: (pair: string) => void;
  onSaveScannerSettings: (settings: ScannerSettings) => void;
  onPortfolioSync: () => void;
  onPortfolioSyncAll: () => void;
  onTagFilter: (tag: string | null) => void;
  onRebalanceApply: () => void;
  onScrubDate: (date: string) => void;
  onPerformanceRangeChange: (range: PerformanceRange) => void;
  onOpenInbox: () => void;
  onCloseInbox: () => void;
  onSaveGoal: (payload: import("../portfolio/GoalsPanel").GoalSavePayload) => void;
  onExportDownload: (path: string, id: string) => void;
  onWalkForward: () => void;
  onMonteCarlo: () => void;
  onPortfolioMc: () => void;
  onHeatmap: () => void;
  onBillingEnroll: () => void;
  onBillingProcess: () => void;
  onBillingSettlement: () => void;
  onBillingMarkPaid: () => void;
  onCopySettlement: (text: string) => void;
  onBillingPaymentPoll: (paymentId: string) => Promise<SettlementData | null>;
  onBillingPaymentConfirmed: (data: SettlementData) => void;
  onBillingAssetChange: (asset: string) => void;
  onBotToggle: (botId: number, enabled: boolean) => void;
  onBotUpdate: (botId: number, payload: import("../dashboard/BotDetailPage").BotUpdatePayload) => void;
  onBotDelete: (botId: number) => void;
  onBotForceTrade: (botId: number, side: "buy" | "sell") => void;
  onOpenBot: (botId: number) => void;
  onCloseBot: () => void;
  onBotSaveParams: (botId: number, strategyId: string, params: Record<string, number>) => void;
  onBotExchangeChange: (exchangeId: string, applyPairs: (pairs: string[]) => void) => void;
  onBotPairChange?: (botId: number, pair: string) => void;
  onOpenGlossary?: (strategyId?: string) => void;
  onCloseGlossary?: () => void;
  onBotApplyBacktest: (botId: number, ranking: import("../api/client").BacktestRanking) => void;
  onCreateBot: () => void;
  onApplyTemplate: (templateId: string) => void;
  onDeleteTemplate: (templateId: string) => void;
  onSaveBotTemplate: (botId: number, name: string) => void;
  onUpdateCheckChange?: (enabled: boolean) => void;
  onDisplayCurrencyChange?: (code: DisplayCurrencyCode) => void;
  onApplyUpdate?: () => void;
  onDeployStrategy?: (strategyId: string) => void;
  onGrowthOptIn?: () => void;
  onGrowthBoost?: () => void;
};

export function renderMainView(
  mount: HTMLElement,
  state: MainViewState,
  callbacks: MainViewCallbacks,
): () => void {
  mount.innerHTML = "";
  let cleanup = (): void => {};

  if (state.view === "settings") {
    mount.appendChild(
      createSettingsView(
        {
          updateStatus: state.updateStatus,
          donations: state.donations,
          canApplyUpdate: state.canApplyUpdate,
          risk: state.dashboard?.risk ?? null,
          strategyId: state.dashboard?.strategy_id ?? null,
          strategyParams: state.strategyParams,
          pairs: state.pairs,
          exitRules: state.exitRules,
          recommendations: state.aiRecommendations ?? null,
          aiDisclaimer: state.aiDisclaimer,
          curatedPresets: state.curatedPresets ?? null,
          curatedVersion: state.curatedVersion,
          referralCode: state.referralCode,
          leaderboard: state.leaderboard ?? null,
          dryRun: state.dashboard?.dry_run ?? true,
        },
        {
          onUpdateCheckChange: callbacks.onUpdateCheckChange,
          onDisplayCurrencyChange: callbacks.onDisplayCurrencyChange,
          onApplyUpdate: callbacks.onApplyUpdate,
          onPause: callbacks.onPause,
          onResume: callbacks.onResume,
          onSaveConfig: callbacks.onSaveConfig,
          onSaveExitRules: callbacks.onSaveExitRules,
          onDeployStrategy: callbacks.onDeployStrategy,
          onGrowthOptIn: callbacks.onGrowthOptIn,
          onGrowthBoost: callbacks.onGrowthBoost,
        },
      ),
    );
    return cleanup;
  }

  if (!state.dashboard) {
    mount.appendChild(createBootSkeleton());
    return cleanup;
  }

  if (state.showInbox) {
    mount.appendChild(createNotificationInbox(state.inboxItems, callbacks.onCloseInbox));
    return cleanup;
  }

  if (state.view === "glossary") {
    const page = createTaGlossaryPage(() => callbacks.onCloseGlossary?.(), state.glossaryFocusId);
    mount.appendChild(page.root);
    return page.cleanup;
  }

  if (state.view === "portfolio") {
    const risk = state.dashboard.risk ?? {};
    const overview = state.portfolioOverview;
    const onboard = createOnboardingChecklist({
      hasPortfolio: Boolean(overview?.holdings?.length),
      hasBots: Boolean(state.dashboard.bots?.length),
      onGoScanner: () => {
        /* parent navigates via callback patch — use window event */
        window.dispatchEvent(new CustomEvent("trendalgo:nav", { detail: "scanner" }));
      },
      onGoBots: () => window.dispatchEvent(new CustomEvent("trendalgo:nav", { detail: "dashboard" })),
      onGoBacktest: () => window.dispatchEvent(new CustomEvent("trendalgo:nav", { detail: "backtest" })),
      onDismiss: () => {
        window.dispatchEvent(new CustomEvent("trendalgo:onboarding-dismiss"));
      },
    });
    if (onboard) mount.appendChild(onboard);
    const panel = createPortfolioPanel(
      {
        overview,
        equityCurve: state.portfolioEquityCurve,
        top10Curve: state.portfolioTop10Curve,
        top10Comparison: state.portfolioTop10Comparison,
        performanceRange: state.portfolioPerformanceRange,
        heatmap: state.portfolioHeatmap,
        rebalanceSuggestions: state.portfolioRebalanceSuggestions as Array<{
          asset: string;
          current_pct: number;
          target_pct: number;
          delta_usd: number;
          action: string;
        }>,
        arbitrage: state.portfolioArbitrage,
        tagFilter: state.portfolioTagFilter,
        platform: state.portfolioPlatform,
        exchangeRegistry: state.exchangeRegistry ?? undefined,
        healthSnapshot: {
          equity_usd: Number(risk.equity_usd ?? state.dashboard.equity_usd ?? 0),
          drawdown_pct: Number(risk.drawdown_pct ?? 0),
          open_exposure_usd: Number(risk.open_exposure_usd ?? 0),
          bot_count: state.dashboard.bot_count ?? 0,
          can_trade: Boolean(risk.can_trade ?? false),
          dry_run: state.dashboard.dry_run ?? true,
          paused: Boolean(risk.paused),
          net_worth_usd: overview?.net_worth_usd,
          max_drawdown_pct: overview?.max_drawdown_pct,
          health_score: overview?.health_score,
        },
        snapshotDates: state.portfolioSnapshotDates,
        selectedSnapshotDate: state.portfolioSelectedDate,
      },
      {
        onSync: callbacks.onPortfolioSync,
        onSelectDate: callbacks.onScrubDate,
        onOpenInbox: callbacks.onOpenInbox,
        onSyncAll: callbacks.onPortfolioSyncAll,
        onTagFilter: callbacks.onTagFilter,
        onRebalanceApply: callbacks.onRebalanceApply,
        onPerformanceRangeChange: callbacks.onPerformanceRangeChange,
        onSaveGoal: callbacks.onSaveGoal,
      },
    );
    mount.appendChild(panel.root);
    cleanup = panel.cleanup;
    return cleanup;
  }

  if (state.view === "dashboard") {
    if (state.selectedBotId != null) {
      if (state.botDetailLoading || !state.botDetail) {
        const label =
          state.dashboard.bots?.find((b) => b.id === state.selectedBotId)?.label ?? t("bots.detail.title");
        mount.appendChild(createBotDetailLoading(label));
        return cleanup;
      }
      const detailPage = createBotDetailPage(
        state.botDetail,
        {
          settings: {
            botId: state.botDetail.bot.id,
            exchanges: (state.exchangeRegistry ?? []).map((e) => ({
              id: e.id,
              name: e.brand || e.id,
            })),
            taLibrary: state.taLibrary.length ? state.taLibrary : [],
            exchangePairs: state.botExchangePairs.length
              ? state.botExchangePairs
              : state.pairs.length
                ? state.pairs
                : [state.dashboard.pair],
            equityLimits: state.botDetail.equity_limits ?? {
              base: { symbol: "BTC", max: 10 },
              quote: { symbol: "USD", max: 50_000 },
              portfolio_usd: 100_000,
              paper: true,
            },
            onExchangeChange: callbacks.onBotExchangeChange,
            onPairChange: (pair) => {
              const id = state.botDetail?.bot.id;
              if (id != null) callbacks.onBotPairChange?.(id, pair);
            },
            onOpenGlossary: () => callbacks.onOpenGlossary?.(),
            botEnabled: state.botDetail.bot.enabled,
            botLimits: state.botLimits ?? undefined,
            guardrailBots: state.dashboard.bots ?? [],
          },
          onBack: callbacks.onCloseBot,
          onSave: callbacks.onBotUpdate,
          onSaveParams: callbacks.onBotSaveParams,
          onApplyBacktest: callbacks.onBotApplyBacktest,
          onSaveTemplate: callbacks.onSaveBotTemplate,
        },
        { paperLocal: state.botDetailLocal },
      );
      mount.appendChild(detailPage.root);
      cleanup = detailPage.cleanup;
      return cleanup;
    }
    mount.appendChild(
      createBotDashboard(
        state.dashboard,
        {
          onOpenBot: callbacks.onOpenBot,
          onToggleEnabled: callbacks.onBotToggle,
          onDelete: callbacks.onBotDelete,
          onForceTrade: callbacks.onBotForceTrade,
          onCreateBot: callbacks.onCreateBot,
          onApplyTemplate: callbacks.onApplyTemplate,
          onDeleteTemplate: callbacks.onDeleteTemplate,
        },
        {
          templates: listBotTemplates(),
          limits: syncBotLimits(state.botLimits ?? DEFAULT_BOT_LIMITS, state.dashboard.bots ?? [], state.dashboard.dry_run),
        },
      ),
    );
    return cleanup;
  }
  if (state.view === "backtest") {
    const panel = createBacktestPanel(
      {
        loading: state.backtestLoading,
        exchangeId: state.fleetExchangeId,
        pair: state.fleetPair,
        stakeUsd: state.fleetStakeUsd,
        exchanges: state.exchangeRegistry ?? [],
        pairs: state.fleetPairs.length ? state.fleetPairs : state.pairs,
        feeSchedule: state.fleetFeeSchedule,
        active: state.fleetActive,
        results: state.fleetResults,
        historyRuns: state.fleetHistoryRuns,
        selectedHistoryJobId: state.fleetSelectedHistoryJobId,
        filterMode: state.fleetFilterMode,
        filterTimeframe: state.fleetFilterTimeframe,
      },
      {
        onRun: callbacks.onRunBacktest,
        onExchangeChange: callbacks.onFleetExchangeChange,
        onPairChange: callbacks.onFleetPairChange,
        onStakeChange: callbacks.onFleetStakeChange,
        onFilterChange: callbacks.onFleetFilterChange,
        onLoadHistoryRun: callbacks.onLoadFleetHistoryRun,
        onCreateBotFromResult: callbacks.onCreateBotFromFleetResult,
        onOpenGlossaryStrategy: (strategyId) => callbacks.onOpenGlossary?.(strategyId),
      },
    );
    mount.appendChild(panel.root);
    mount.appendChild(
      createResearchToolsPanel(state.researchResults, {
        onWalkForward: callbacks.onWalkForward,
        onMonteCarlo: callbacks.onMonteCarlo,
        onPortfolioMc: callbacks.onPortfolioMc,
        onHeatmap: callbacks.onHeatmap,
      }),
    );
    cleanup = panel.cleanup;
    return cleanup;
  }
  if (state.view === "export") {
    if (!state.exportItems.length) {
      const empty = document.createElement("section");
      empty.className = "gp-panel";
      empty.dataset.testid = "export-empty";
      empty.innerHTML = `<h2 class="gp-panel-title">${t("export.title")}</h2><p class="gp-empty">${t("empty.export")}</p>`;
      mount.appendChild(empty);
    } else {
      mount.appendChild(
        createExportHub(state.exportItems, (path, id) => callbacks.onExportDownload(path, id)),
      );
    }
    if (state.diversification) {
      mount.appendChild(
        createDiversificationPanel(
          state.diversification.suggestions,
          state.diversification.correlation,
        ),
      );
    }
    return cleanup;
  }
  if (state.view === "billing") {
    if (!state.billingDashboard) {
      const empty = document.createElement("section");
      empty.className = "gp-panel";
      empty.dataset.testid = "billing-empty";
      empty.innerHTML = `<h2 class="gp-panel-title">${t("nav.billing")}</h2><p class="gp-empty">${t("empty.billing")}</p>`;
      mount.appendChild(empty);
      return cleanup;
    }
    mount.appendChild(
      createBillingDashboard(state.billingDashboard, {
        onEnroll: callbacks.onBillingEnroll,
        onProcessTrades: callbacks.onBillingProcess,
        onOpenSettlement: callbacks.onBillingSettlement,
        onMarkPaid: callbacks.onBillingMarkPaid,
      }),
    );
    if (state.showBillingSettlement && state.billingSettlement) {
      const assets = (state.billingDashboard?.payment_assets ?? []).map((row) => ({
        asset: String(row.asset ?? ""),
        label: String(row.label ?? row.asset ?? ""),
        chain: String(row.chain ?? ""),
      }));
      mount.appendChild(
        createSettlementPanel(state.billingSettlement, {
          onCopy: callbacks.onCopySettlement,
          onPoll: callbacks.onBillingPaymentPoll,
          onConfirmed: callbacks.onBillingPaymentConfirmed,
          assets,
          selectedAsset: state.billingSettlementAsset ?? state.billingSettlement.asset,
          onAssetChange: callbacks.onBillingAssetChange,
        }),
      );
    }
    return cleanup;
  }
  if (state.view === "scanner") {
    if (!state.scannerSettings) {
      const empty = document.createElement("section");
      empty.className = "gp-panel";
      empty.dataset.testid = "scanner-empty";
      empty.innerHTML = `<h2 class="gp-panel-title">${t("nav.scanner")}</h2><p class="gp-empty">${t("empty.scanner")}</p>`;
      mount.appendChild(empty);
      return cleanup;
    }
    mount.appendChild(
      createScannerPanel(
        state.scannerSnapshot,
        state.scannerSettings,
        state.scannerWatchlist,
        state.scannerLoading,
        {
          onRunScan: callbacks.onRunScanner,
          onPin: callbacks.onPinPair,
          onSaveSettings: callbacks.onSaveScannerSettings,
        },
      ),
    );
    return cleanup;
  }
  mount.appendChild(createDebugLogViewer(state.debugLogs));
  return cleanup;
}
