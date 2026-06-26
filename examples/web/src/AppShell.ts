import { APP_VERSION } from "./about/aboutSession";
import type { DonationConfig } from "./about/types";
import type { BacktestPayload, DashboardData } from "./api/client";
import { createAboutPanel } from "./components/AboutPanel";
import { createSettingsPanel } from "./components/SettingsPanel";
import { createThemeToggle } from "./components/ThemeToggle";
import { isOnline } from "./greet";
import { t } from "./i18n";
import { bindPanelDialog } from "./panelDialog";
import type { ExportItem } from "./export/ExportHub";
import type { LibraryRun } from "./backtest/library/BacktestLibrary";
import type { ScannerSettings, ScannerSnapshot } from "./scanner/ScannerPanel";
import type { BillingDashboardData } from "./billing/BillingDashboard";
import type { SettlementData } from "./billing/pay/SettlementPanel";
import type { ExitRulesState } from "./config/ConfigForm";
import type { StrategyTemplate } from "./strategies/StrategiesPanel";
import type { Recommendation } from "./ai/RecommenderPanel";
import type { CuratedPreset } from "./ai/CuratedLibraryPanel";
import { createHealthWidget } from "./shell/HealthWidget";
import { createMobileNav, type AppView } from "./shell/MobileNav";
import { renderMainView } from "./shell/renderMainView";

let dialogCleanup: (() => void) | undefined;
let viewCleanup: (() => void) | undefined;

export type AppShellState = {
  view: AppView;
  showAbout: boolean;
  showSettings: boolean;
  updateStatus: string;
  donations: DonationConfig;
  dashboard: DashboardData | null;
  backtest: BacktestPayload | null;
  backtestLoading: boolean;
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
  portfolioSnapshotDates: string[];
  portfolioHeatmap: Array<{ asset: string; return_pct: number; volatility_pct: number }>;
  portfolioSelectedDate: string | null;
  portfolioRebalanceSuggestions: Array<Record<string, unknown>>;
  portfolioArbitrage: { alerts: Array<Record<string, unknown>>; disclaimer: string };
  portfolioTagFilter: string | null;
  showInbox: boolean;
  inboxItems: import("./notifications/Inbox").InboxItem[];
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
  portfolioPlatform: import("./platform/PlatformPanel").PlatformData | null;
  exchangeRegistry: import("./portfolio/AccountsPanel").ExchangeRegistryEntry[] | null;
};

export type AppShellCallbacks = {
  onState: (next: Partial<AppShellState>) => void;
  onUpdateCheckChange?: (enabled: boolean) => void;
  onApplyUpdate?: () => void;
  canApplyUpdate?: boolean;
  onRunBacktest?: () => void;
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
  onOpenInbox?: () => void;
  onCloseInbox?: () => void;
  onDeployStrategy?: (id: string) => void;
  onExportStrategy?: (id: string) => void;
  onImportStrategy?: (json: string) => void;
  onComposeStrategy?: (code: string) => void;
  onCloneBacktest?: (id: number) => void;
  onCompareBacktests?: (ids: number[]) => void;
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
  onLeaderboardOptIn?: () => void;
  onBoostMode?: () => void;
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
      <div class="gp-header">
        <h1 class="gp-title">${t("app.title")}</h1>
        <div class="gp-header-actions">
          <button type="button" class="gp-settings-btn" data-settings-open aria-label="${t("settings.open")}">⚙</button>
          <button type="button" class="gp-about-btn" data-about-open aria-label="${t("about.open")}">i</button>
        </div>
      </div>
      <p class="gp-body" data-testid="status">${t(statusKey)}</p>
      ${
        showHomeUpdate
          ? `<p class="gp-update-banner" data-testid="home-update-status" aria-live="polite">${state.updateStatus}</p>`
          : ""
      }
      <div data-health-mount></div>
      <div data-main-mount></div>
      <div data-nav-mount></div>
      <div data-panel-mount></div>
    </main>
  `;

  const actions = root.querySelector<HTMLDivElement>(".gp-header-actions");
  if (actions) actions.insertBefore(createThemeToggle(), actions.firstChild);

  root.querySelector("[data-about-open]")?.addEventListener("click", () => {
    callbacks.onState({ showAbout: !state.showAbout, showSettings: false });
  });
  root.querySelector("[data-settings-open]")?.addEventListener("click", () => {
    callbacks.onState({ showSettings: !state.showSettings, showAbout: false });
  });

  const healthMount = root.querySelector("[data-health-mount]");
  if (healthMount) {
    healthMount.innerHTML = "";
    const d = state.dashboard;
    const risk = d?.risk ?? {};
    healthMount.appendChild(
      createHealthWidget({
        equity_usd: Number(risk.equity_usd ?? d?.equity_usd ?? 0),
        drawdown_pct: Number(risk.drawdown_pct ?? 0),
        open_exposure_usd: Number(risk.open_exposure_usd ?? 0),
        bot_count: d?.bot_count ?? 0,
        can_trade: Boolean(risk.can_trade ?? false),
        dry_run: d?.dry_run ?? true,
        paused: Boolean(risk.paused),
      }),
    );
  }

  const mainMount = root.querySelector("[data-main-mount]");
  viewCleanup?.();
  viewCleanup = undefined;
  if (mainMount) {
    viewCleanup = renderMainView(mainMount as HTMLElement, state, {
      onRunBacktest: () => callbacks.onRunBacktest?.(),
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
      onOpenInbox: () => callbacks.onOpenInbox?.(),
      onCloseInbox: () => callbacks.onCloseInbox?.(),
      onDeployStrategy: (id) => callbacks.onDeployStrategy?.(id),
      onExportStrategy: (id) => callbacks.onExportStrategy?.(id),
      onImportStrategy: (json) => callbacks.onImportStrategy?.(json),
      onComposeStrategy: (code) => callbacks.onComposeStrategy?.(code),
      onCloneBacktest: (id) => callbacks.onCloneBacktest?.(id),
      onCompareBacktests: (ids) => callbacks.onCompareBacktests?.(ids),
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
      onLeaderboardOptIn: () => callbacks.onLeaderboardOptIn?.(),
      onBoostMode: () => callbacks.onBoostMode?.(),
    });
  }

  const navMount = root.querySelector("[data-nav-mount]");
  if (navMount) {
    navMount.innerHTML = "";
    navMount.appendChild(
      createMobileNav(state.view, (view) => callbacks.onState({ view, showAbout: false, showSettings: false })),
    );
  }

  const mount = root.querySelector("[data-panel-mount]");
  if (!mount) return;

  dialogCleanup?.();
  dialogCleanup = undefined;
  mount.innerHTML = "";

  if (state.showSettings) {
    const panel = createSettingsPanel({
      onClose: () => callbacks.onState({ showSettings: false }),
      onUpdateCheckChange: callbacks.onUpdateCheckChange,
    });
    mount.appendChild(panel);
    dialogCleanup = bindPanelDialog(panel, () => callbacks.onState({ showSettings: false }));
    return;
  }

  if (!state.showAbout) return;

  mount.appendChild(
    createAboutPanel(
      {
        version: APP_VERSION,
        updateStatus: state.updateStatus,
        donations: state.donations,
        canApplyUpdate: callbacks.canApplyUpdate,
      },
      () => callbacks.onState({ showAbout: false }),
      callbacks.onApplyUpdate,
    ),
  );
  const aboutPanel = mount.lastElementChild as HTMLElement;
  dialogCleanup = bindPanelDialog(aboutPanel, () => callbacks.onState({ showAbout: false }));
}
