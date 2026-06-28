import { createPortfolioPerformanceChart, type PerformanceRange } from "./PortfolioPerformanceChart";
import { t } from "../i18n";
import {
  createBotUnifiedSection,
  createPortfolioHero,
  createQuickActions,
  type PortfolioCallbacks,
  type PortfolioOverviewData,
} from "./PortfolioSections";
import { createHeatmap, heatmapFromHoldings } from "./Heatmap";
import { mountHoldingsPanel } from "./HoldingsPanel";
import { mountAccountsPanel, type ExchangeRegistryEntry } from "./AccountsPanel";
import { createArbitragePanel } from "./ArbitragePanel";
import { createGoalsPanel, type GoalSavePayload } from "./GoalsPanel";
import { createRebalancePanel } from "./RebalancePanel";
import { createPlatformPanel, type PlatformData } from "../platform/PlatformPanel";
import { createHealthWidget, type HealthSnapshot } from "../shell/HealthWidget";

export type PortfolioPanelState = {
  overview: PortfolioOverviewData | null;
  equityCurve: import("../charts/EquityChart").EquityPoint[];
  top10Curve: import("../charts/EquityChart").EquityPoint[];
  top10Comparison: import("../charts/EquityChart").PerformanceComparison | null;
  performanceRange: PerformanceRange;
  heatmap: Array<{ asset: string; return_pct: number; volatility_pct: number }>;
  rebalanceSuggestions: Array<{
    asset: string;
    current_pct: number;
    target_pct: number;
    delta_usd: number;
    action: string;
  }>;
  arbitrage: { alerts: Array<Record<string, unknown>>; disclaimer: string };
  tagFilter: string | null;
  platform: PlatformData | null;
  exchangeRegistry?: ExchangeRegistryEntry[];
  healthSnapshot?: HealthSnapshot;
};

export function createPortfolioPanel(
  state: PortfolioPanelState,
  callbacks: PortfolioCallbacks & {
    onTagFilter: (tag: string | null) => void;
    onRebalanceApply: () => void;
    onSyncAll: () => void;
    onPerformanceRangeChange: (range: PerformanceRange) => void;
    onSaveGoal: (payload: GoalSavePayload) => void;
  },
): { root: HTMLElement; cleanup: () => void } {
  const root = document.createElement("div");
  root.className = "gp-portfolio-panel";
  root.dataset.testid = "portfolio-panel";
  let chartCleanup = (): void => {};

  if (!state.overview) {
    root.innerHTML = `<p>${t("portfolio.loading")}</p>`;
    return { root, cleanup: () => chartCleanup() };
  }

  root.appendChild(createPortfolioHero(state.overview));
  root.appendChild(createQuickActions({ ...callbacks, onSync: callbacks.onSyncAll }));

  if (state.overview.accounts?.length) {
    const accountsMount = document.createElement("div");
    accountsMount.dataset.testid = "portfolio-accounts-mount";
    root.appendChild(accountsMount);
    mountAccountsPanel(
      accountsMount,
      state.overview.accounts,
      state.overview.net_worth_usd,
      state.exchangeRegistry,
    );
  }

  const perfChart = createPortfolioPerformanceChart(
    state.equityCurve,
    state.top10Curve,
    state.top10Comparison,
    state.performanceRange,
    callbacks.onPerformanceRangeChange,
  );
  root.appendChild(perfChart.root);
  chartCleanup = perfChart.cleanup;

  const holdingsMount = document.createElement("div");
  holdingsMount.dataset.testid = "holdings-table-mount";
  root.appendChild(holdingsMount);
  mountHoldingsPanel(holdingsMount, state.overview.holdings, {
    portfolioTotalUsd: state.overview.net_worth_usd,
    tagFilter: state.tagFilter,
    onTagFilter: callbacks.onTagFilter,
  });

  root.appendChild(createHeatmap(heatmapFromHoldings(state.overview.holdings)));

  if (state.healthSnapshot) {
    root.appendChild(createHealthWidget(state.healthSnapshot));
  }

  root.appendChild(
    createGoalsPanel(state.overview.performance_goal ?? null, callbacks.onSaveGoal),
  );
  root.appendChild(
    createRebalancePanel(state.rebalanceSuggestions, callbacks.onRebalanceApply),
  );
  root.appendChild(
    createArbitragePanel(
      state.arbitrage.alerts as Array<{
        pair: string;
        spread_pct: number;
        buy_exchange: string;
        sell_exchange: string;
        informational_only: boolean;
      }>,
      state.arbitrage.disclaimer,
    ),
  );

  root.appendChild(createBotUnifiedSection(state.overview.bot));
  if (state.platform) {
    root.appendChild(createPlatformPanel(state.platform));
  }

  return {
    root,
    cleanup: () => chartCleanup(),
  };
}
