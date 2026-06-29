import type { DonationConfig } from "./about/types";
import type { BacktestPayload, BotDetailData, DashboardData, ExchangeFeeSchedule, FleetActiveSnapshot, FleetLatestPayload } from "./api/client";
import { isOnline } from "./greet";
import { t } from "./i18n";
import type { ExportItem } from "./export/ExportHub";
import type { ScannerSettings, ScannerSnapshot } from "./scanner/ScannerPanel";
import type { BillingDashboardData } from "./billing/BillingDashboard";
import type { SettlementData } from "./billing/pay/SettlementPanel";
import type { ExitRulesState } from "./config/ConfigForm";
import type { DisplayCurrencyCode } from "./settings/displayCurrency";
import { createMobileNav, type AppView } from "./shell/MobileNav";
import { renderMainView } from "./shell/renderMainView";

let viewCleanup: (() => void) | undefined;

export type AppShellState = {
  view: AppView;
  updateStatus: string;
  donations: DonationConfig;
  dashboard: DashboardData | null;
  backtest: BacktestPayload | null;
  backtestLoading: boolean;
  fleetExchangeId: string;
  fleetPair: string;
  fleetStakeUsd: number;
  fleetPairs: string[];
  fleetActive: FleetActiveSnapshot | null;
  fleetResults: FleetLatestPayload | null;
  fleetFeeSchedule: ExchangeFeeSchedule | null;
  fleetFeeCatalog: ExchangeFeeSchedule[];
  fleetHistoryRuns: import("./api/client").FleetHistoryEntry[];
  fleetSelectedHistoryJobId: string | null;
  fleetFilterMode: "all" | "timeframe" | "strategy";
  fleetFilterTimeframe: string;
  strategyParams: Record<string, number>;
  pairs: string[];
  debugLogs: string[];
  apiOnline: boolean;
  scannerSnapshot: ScannerSnapshot | null;
  scannerSettings: ScannerSettings | null;
  scannerWatchlist: string[];
  scannerLoading: boolean;
  portfolioOverview: import("./portfolio/PortfolioSections").PortfolioOverviewData | null;
  portfolioEquityCurve: import("./charts/EquityChart").EquityPoint[];
  portfolioTop10Curve: import("./charts/EquityChart").EquityPoint[];
  portfolioTop10Comparison: import("./charts/EquityChart").PerformanceComparison | null;
  portfolioPerformanceRange: import("./portfolio/PortfolioPerformanceChart").PerformanceRange;
  portfolioSnapshotDates: string[];
  portfolioHeatmap: Array<{ asset: string; return_pct: number; volatility_pct: number }>;
  portfolioSelectedDate: string | null;
  portfolioRebalanceSuggestions: Array<Record<string, unknown>>;
  portfolioArbitrage: { alerts: Array<Record<string, unknown>>; disclaimer: string };
  portfolioTagFilter: string | null;
  showInbox: boolean;
  inboxItems: import("./notifications/Inbox").InboxItem[];
  exportItems: ExportItem[];
  researchResults: Record<string, unknown>;
  diversification: { suggestions: string[]; correlation: { assets: string[]; matrix: number[][] } } | null;
  exitRules: ExitRulesState | null;
  billingDashboard: BillingDashboardData | null;
  billingSettlement: SettlementData | null;
  showBillingSettlement: boolean;
  billingSettlementAsset?: string;
  portfolioPlatform: import("./platform/PlatformPanel").PlatformData | null;
  exchangeRegistry: import("./portfolio/AccountsPanel").ExchangeRegistryEntry[] | null;
  selectedBotId: number | null;
  botDetail: BotDetailData | null;
  botDetailLoading: boolean;
  botDetailError: string | null;
  botDetailLocal: boolean;
  taLibrary: import("./api/client").TaLibraryCategory[];
  botExchangePairs: string[];
  botLimits: import("./bots/botGuardrails").BotLimits | null;
  glossaryReturnView: AppView | null;
  glossaryFocusId: string | null;
};

export type AppShellCallbacks = {
  onState: (next: Partial<AppShellState>) => void;
  onUpdateCheckChange?: (enabled: boolean) => void;
  onDisplayCurrencyChange?: (code: DisplayCurrencyCode) => void;
  onApplyUpdate?: () => void;
  canApplyUpdate?: boolean;
  onRunBacktest?: () => void;
  onFleetExchangeChange?: (exchangeId: string) => void;
  onFleetPairChange?: (pair: string) => void;
  onFleetStakeChange?: (stakeUsd: number) => void;
  onFleetFilterChange?: (mode: "all" | "timeframe" | "strategy", timeframe?: string) => void;
  onLoadFleetHistoryRun?: (jobId: string) => void;
  onCreateBotFromFleetResult?: (row: import("./api/client").FleetResultRow) => void;
  onPause?: () => void;
  onResume?: () => void;
  onSaveConfig?: (params: Record<string, number>) => void;
  onSaveExitRules?: (rules: ExitRulesState) => void;
  onRunScanner?: () => void;
  onPinPair?: (pair: string) => void;
  onSaveScannerSettings?: (settings: Record<string, unknown>) => void;
  onPortfolioSync?: () => void;
  onPortfolioSyncAll?: () => void;
  onTagFilter?: (tag: string | null) => void;
  onRebalanceApply?: () => void;
  onScrubDate?: (date: string) => void;
  onPerformanceRangeChange?: (range: import("./portfolio/PortfolioPerformanceChart").PerformanceRange) => void;
  onSaveGoal?: (payload: import("./portfolio/GoalsPanel").GoalSavePayload) => void;
  onBotToggle?: (botId: number, enabled: boolean) => void;
  onBotUpdate?: (botId: number, payload: import("./dashboard/BotDetailPage").BotUpdatePayload) => void;
  onBotDelete?: (botId: number) => void;
  onBotForceTrade?: (botId: number, side: "buy" | "sell") => void;
  onOpenBot?: (botId: number) => void;
  onCloseBot?: () => void;
  onBotSaveParams?: (botId: number, strategyId: string, params: Record<string, number>) => void;
  onBotExchangeChange?: (exchangeId: string, applyPairs: (pairs: string[]) => void) => void;
  onBotPairChange?: (botId: number, pair: string) => void;
  onOpenGlossary?: (strategyId?: string) => void;
  onCloseGlossary?: () => void;
  onBotApplyBacktest?: (botId: number, ranking: import("./api/client").BacktestRanking) => void;
  onCreateBot?: () => void;
  onApplyTemplate?: (templateId: string) => void;
  onDeleteTemplate?: (templateId: string) => void;
  onSaveBotTemplate?: (botId: number, name: string) => void;
  onOpenInbox?: () => void;
  onCloseInbox?: () => void;
  onExportDownload?: (path: string, id: string) => void;
  onWalkForward?: () => void;
  onMonteCarlo?: () => void;
  onPortfolioMc?: () => void;
  onHeatmap?: () => void;
  onBillingEnroll?: () => void;
  onBillingProcess?: () => void;
  onBillingSettlement?: () => void;
  onBillingMarkPaid?: () => void;
  onCopySettlement?: (text: string) => void;
  onBillingLightning?: () => void;
  onBillingPaymentPoll?: (paymentId: string) => Promise<import("./billing/pay/SettlementPanel").SettlementData | null>;
  onBillingPaymentConfirmed?: (data: import("./billing/pay/SettlementPanel").SettlementData) => void;
  onBillingAssetChange?: (asset: string) => void;
};

export function createAppShell(
  root: HTMLElement,
  state: AppShellState,
  callbacks: AppShellCallbacks,
): void {
  const online = isOnline();
  const statusKey = state.apiOnline
    ? online
      ? "app.status.online"
      : "app.status.offline"
    : "app.status.api_offline";
  const currentUpdateLabel = t("about.update.current");
  const showHomeUpdate = state.updateStatus !== currentUpdateLabel;

  root.innerHTML = `
    <main class="gp-app">
      <div class="gp-sticky-top">
        <div class="gp-header">
          <h1 class="gp-title">${t("app.title")}</h1>
        </div>
        <div data-nav-mount></div>
      </div>
      <div class="gp-scroll-body">
      <p class="gp-body" data-testid="status">${t(statusKey)}</p>
      ${state.botDetailError ? `<p class="gp-error-banner" data-testid="bot-detail-error" role="alert">${state.botDetailError}</p>` : ""}
      ${
        showHomeUpdate
          ? `<p class="gp-update-banner" data-testid="home-update-status" aria-live="polite">${state.updateStatus}</p>`
          : ""
      }
      <div data-main-mount></div>
      </div>
    </main>
  `;

  const navMount = root.querySelector("[data-nav-mount]");
  if (navMount) {
    navMount.innerHTML = "";
    navMount.appendChild(
      createMobileNav(state.view, (view) => callbacks.onState({ view })),
    );
  }

  const mainMount = root.querySelector("[data-main-mount]");
  viewCleanup?.();
  viewCleanup = undefined;
  if (mainMount) {
    viewCleanup = renderMainView(
      mainMount as HTMLElement,
      {
        ...state,
        canApplyUpdate: callbacks.canApplyUpdate,
      },
      {
      onRunBacktest: () => callbacks.onRunBacktest?.(),
      onFleetExchangeChange: (exchangeId) => callbacks.onFleetExchangeChange?.(exchangeId),
      onFleetPairChange: (pair) => callbacks.onFleetPairChange?.(pair),
      onFleetStakeChange: (stakeUsd) => callbacks.onFleetStakeChange?.(stakeUsd),
      onFleetFilterChange: (mode, timeframe) => callbacks.onFleetFilterChange?.(mode, timeframe),
      onLoadFleetHistoryRun: (jobId) => callbacks.onLoadFleetHistoryRun?.(jobId),
      onCreateBotFromFleetResult: (row) => callbacks.onCreateBotFromFleetResult?.(row),
      onPause: () => callbacks.onPause?.(),
      onResume: () => callbacks.onResume?.(),
      onSaveConfig: (params) => callbacks.onSaveConfig?.(params),
      onSaveExitRules: (rules) => callbacks.onSaveExitRules?.(rules),
      onRunScanner: () => callbacks.onRunScanner?.(),
      onPinPair: (pair) => callbacks.onPinPair?.(pair),
      onSaveScannerSettings: (settings) => callbacks.onSaveScannerSettings?.(settings),
      onPortfolioSync: () => callbacks.onPortfolioSync?.(),
      onPortfolioSyncAll: () => callbacks.onPortfolioSyncAll?.(),
      onTagFilter: (tag) => callbacks.onTagFilter?.(tag),
      onRebalanceApply: () => callbacks.onRebalanceApply?.(),
      onScrubDate: (date) => callbacks.onScrubDate?.(date),
      onPerformanceRangeChange: (range) => callbacks.onPerformanceRangeChange?.(range),
      onSaveGoal: (payload) => callbacks.onSaveGoal?.(payload),
      onBotToggle: (botId, enabled) => callbacks.onBotToggle?.(botId, enabled),
      onBotUpdate: (botId, payload) => callbacks.onBotUpdate?.(botId, payload),
      onBotDelete: (botId) => callbacks.onBotDelete?.(botId),
      onBotForceTrade: (botId, side) => callbacks.onBotForceTrade?.(botId, side),
      onOpenBot: (botId) => callbacks.onOpenBot?.(botId),
      onCloseBot: () => callbacks.onCloseBot?.(),
      onBotSaveParams: (botId, strategyId, params) =>
        callbacks.onBotSaveParams?.(botId, strategyId, params),
      onBotExchangeChange: (exchangeId, applyPairs) =>
        callbacks.onBotExchangeChange?.(exchangeId, applyPairs),
      onBotPairChange: (botId, pair) => callbacks.onBotPairChange?.(botId, pair),
      onOpenGlossary: (strategyId) => callbacks.onOpenGlossary?.(strategyId),
      onCloseGlossary: () => callbacks.onCloseGlossary?.(),
      onBotApplyBacktest: (botId, ranking) => callbacks.onBotApplyBacktest?.(botId, ranking),
      onCreateBot: () => callbacks.onCreateBot?.(),
      onApplyTemplate: (id) => callbacks.onApplyTemplate?.(id),
      onDeleteTemplate: (id) => callbacks.onDeleteTemplate?.(id),
      onSaveBotTemplate: (botId, name) => callbacks.onSaveBotTemplate?.(botId, name),
      onOpenInbox: () => callbacks.onOpenInbox?.(),
      onCloseInbox: () => callbacks.onCloseInbox?.(),
      onExportDownload: (path, id) => callbacks.onExportDownload?.(path, id),
      onWalkForward: () => callbacks.onWalkForward?.(),
      onMonteCarlo: () => callbacks.onMonteCarlo?.(),
      onPortfolioMc: () => callbacks.onPortfolioMc?.(),
      onHeatmap: () => callbacks.onHeatmap?.(),
      onBillingEnroll: () => callbacks.onBillingEnroll?.(),
      onBillingProcess: () => callbacks.onBillingProcess?.(),
      onBillingSettlement: () => callbacks.onBillingSettlement?.(),
      onBillingMarkPaid: () => callbacks.onBillingMarkPaid?.(),
      onCopySettlement: (text) => callbacks.onCopySettlement?.(text),
      onBillingLightning: () => callbacks.onBillingLightning?.(),
      onBillingPaymentPoll: (paymentId) => callbacks.onBillingPaymentPoll?.(paymentId) ?? Promise.resolve(null),
      onBillingPaymentConfirmed: (data) => callbacks.onBillingPaymentConfirmed?.(data),
      onBillingAssetChange: (asset) => callbacks.onBillingAssetChange?.(asset),
      onUpdateCheckChange: callbacks.onUpdateCheckChange,
      onDisplayCurrencyChange: callbacks.onDisplayCurrencyChange,
      onApplyUpdate: callbacks.onApplyUpdate,
    });
  }
}
