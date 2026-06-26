import { createBacktestPanel } from "../backtest/BacktestPanel";
import type { BacktestPayload, DashboardData } from "../api/client";
import { createConfigForm, type ExitRulesState } from "../config/ConfigForm";
import { createBotDashboard } from "../dashboard/BotDashboard";
import { createDebugLogViewer } from "../debug/DebugLogViewer";
import { createNotificationInbox, type InboxItem } from "../notifications/Inbox";
import { createPortfolioPanel } from "../portfolio/PortfolioPanel";
import type { PortfolioOverviewData } from "../portfolio/PortfolioSections";
import { createRiskPanel } from "../risk/RiskPanel";
import { createScannerPanel } from "../scanner/ScannerPanel";
import type { ScannerSettings, ScannerSnapshot } from "../scanner/ScannerPanel";
import { createStrategiesPanel } from "../strategies/StrategiesPanel";
import type { StrategyTemplate } from "../strategies/StrategiesPanel";
import { createRecommenderPanel, type Recommendation } from "../ai/RecommenderPanel";
import { createCuratedLibraryPanel, type CuratedPreset } from "../ai/CuratedLibraryPanel";
import { createGrowthPanel } from "../growth/GrowthPanel";
import type { EquityPoint } from "../charts/EquityChart";
import { createExportHub, type ExportItem } from "../export/ExportHub";
import { createBillingDashboard, type BillingDashboardData } from "../billing/BillingDashboard";
import { createSettlementPanel, type SettlementData } from "../billing/pay/SettlementPanel";
import { createBacktestVisualizer } from "../research/BacktestVisualizer";
import { createDiversificationPanel } from "../research/DiversificationPanel";
import { createResearchToolsPanel } from "../research/ResearchTools";
import type { LibraryRun } from "../backtest/library/BacktestLibrary";
import type { AppView } from "./MobileNav";

export type MainViewState = {
  view: AppView;
  dashboard: DashboardData | null;
  backtest: BacktestPayload | null;
  backtestLoading: boolean;
  strategyParams: Record<string, number>;
  pairs: string[];
  debugLogs: string[];
  scannerSnapshot: ScannerSnapshot | null;
  scannerSettings: ScannerSettings | null;
  scannerWatchlist: string[];
  scannerLoading: boolean;
  portfolioOverview: PortfolioOverviewData | null;
  portfolioEquityCurve: EquityPoint[];
  portfolioSnapshotDates: string[];
  portfolioHeatmap: Array<{ asset: string; return_pct: number; volatility_pct: number }>;
  portfolioSelectedDate: string | null;
  portfolioRebalanceSuggestions: Array<Record<string, unknown>>;
  portfolioArbitrage: { alerts: Array<Record<string, unknown>>; disclaimer: string };
  portfolioTagFilter: string | null;
  showInbox: boolean;
  inboxItems: InboxItem[];
  strategyTemplates: StrategyTemplate[];
  composerCode: string;
  backtestLibrary: LibraryRun[];
  exportItems: ExportItem[];
  researchResults: Record<string, unknown>;
  diversification: { suggestions: string[]; correlation: { assets: string[]; matrix: number[][] } } | null;
  exitRules: ExitRulesState | null;
  billingDashboard: BillingDashboardData | null;
  billingSettlement: SettlementData | null;
  showBillingSettlement: boolean;
  aiRecommendations: Recommendation[];
  aiDisclaimer: string;
  curatedPresets: CuratedPreset[];
  curatedVersion: string;
  referralCode: string;
  leaderboardRows: Array<{ pseudonym: string; score_usd: number }>;
  portfolioPlatform: import("../platform/PlatformPanel").PlatformData | null;
  exchangeRegistry: import("../portfolio/AccountsPanel").ExchangeRegistryEntry[] | null;
};

export type MainViewCallbacks = {
  onRunBacktest: () => void;
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
  onOpenInbox: () => void;
  onCloseInbox: () => void;
  onDeployStrategy: (id: string) => void;
  onExportStrategy: (id: string) => void;
  onImportStrategy: (json: string) => void;
  onComposeStrategy: (code: string) => void;
  onCloneBacktest: (id: number) => void;
  onCompareBacktests: (ids: number[]) => void;
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
  onBillingLightning: () => void;
  onLeaderboardOptIn: () => void;
  onBoostMode: () => void;
};

export function renderMainView(
  mount: HTMLElement,
  state: MainViewState,
  callbacks: MainViewCallbacks,
): () => void {
  mount.innerHTML = "";
  let cleanup = (): void => {};

  if (!state.dashboard) return cleanup;

  if (state.showInbox) {
    mount.appendChild(createNotificationInbox(state.inboxItems, callbacks.onCloseInbox));
    return cleanup;
  }

  if (state.view === "portfolio") {
    const panel = createPortfolioPanel(
      {
        overview: state.portfolioOverview,
        equityCurve: state.portfolioEquityCurve,
        snapshotDates: state.portfolioSnapshotDates,
        heatmap: state.portfolioHeatmap,
        selectedDate: state.portfolioSelectedDate,
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
      },
      {
        onSync: callbacks.onPortfolioSync,
        onSelectDate: callbacks.onScrubDate,
        onOpenInbox: callbacks.onOpenInbox,
        onScrubDate: callbacks.onScrubDate,
        onSyncAll: callbacks.onPortfolioSyncAll,
        onTagFilter: callbacks.onTagFilter,
        onRebalanceApply: callbacks.onRebalanceApply,
      },
    );
    mount.appendChild(panel.root);
    cleanup = panel.cleanup;
    return cleanup;
  }

  if (state.view === "dashboard") {
    mount.appendChild(createBotDashboard(state.dashboard));
    return cleanup;
  }
  if (state.view === "strategies") {
    mount.appendChild(
      createStrategiesPanel(state.strategyTemplates, state.composerCode, {
        onDeploy: callbacks.onDeployStrategy,
        onExport: callbacks.onExportStrategy,
        onImport: callbacks.onImportStrategy,
        onCompose: callbacks.onComposeStrategy,
      }),
    );
    if (state.aiRecommendations.length) {
      mount.appendChild(
        createRecommenderPanel(
          state.aiRecommendations,
          state.aiDisclaimer,
          callbacks.onDeployStrategy,
        ),
      );
    }
    if (state.curatedPresets.length) {
      mount.appendChild(
        createCuratedLibraryPanel(
          state.curatedPresets,
          state.curatedVersion,
          callbacks.onDeployStrategy,
        ),
      );
    }
    mount.appendChild(
      createGrowthPanel(
        state.referralCode,
        state.leaderboardRows,
        callbacks.onLeaderboardOptIn,
        callbacks.onBoostMode,
      ),
    );
    return cleanup;
  }
  if (state.view === "backtest") {
    const panel = createBacktestPanel(
      state.backtest,
      state.backtestLoading,
      {
        onRun: callbacks.onRunBacktest,
        onCloneRun: callbacks.onCloneBacktest,
        onCompareRuns: callbacks.onCompareBacktests,
      },
      state.backtestLibrary,
    );
    mount.appendChild(panel.root);
    mount.appendChild(createBacktestVisualizer(state.backtest));
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
    mount.appendChild(
      createExportHub(state.exportItems, (path, id) => callbacks.onExportDownload(path, id)),
    );
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
  if (state.view === "billing" && state.billingDashboard) {
    mount.appendChild(
      createBillingDashboard(state.billingDashboard, {
        onEnroll: callbacks.onBillingEnroll,
        onProcessTrades: callbacks.onBillingProcess,
        onOpenSettlement: callbacks.onBillingSettlement,
        onMarkPaid: callbacks.onBillingMarkPaid,
      }),
    );
    if (state.showBillingSettlement && state.billingSettlement) {
      mount.appendChild(
        createSettlementPanel(
          state.billingSettlement,
          callbacks.onCopySettlement,
          callbacks.onBillingLightning,
        ),
      );
    }
    return cleanup;
  }
  if (state.view === "scanner" && state.scannerSettings) {
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
  if (state.view === "risk") {
    mount.appendChild(
      createRiskPanel(state.dashboard.risk, {
        onPause: callbacks.onPause,
        onResume: callbacks.onResume,
      }),
    );
    return cleanup;
  }
  if (state.view === "config") {
    mount.appendChild(
      createConfigForm(
        state.dashboard.strategy_id,
        state.strategyParams,
        state.pairs,
        { onSave: callbacks.onSaveConfig, onSaveExitRules: callbacks.onSaveExitRules },
        state.exitRules ?? undefined,
      ),
    );
    return cleanup;
  }
  mount.appendChild(createDebugLogViewer(state.debugLogs));
  return cleanup;
}
