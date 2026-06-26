import { renderEquityChart, type EquityPoint } from "../charts/EquityChart";
import { t } from "../i18n";
import {
  createAllocationSection,
  createBotUnifiedSection,
  createHoldingsTable,
  createPeriodComparison,
  createPlBreakdown,
  createPortfolioHero,
  createQuickActions,
  type PortfolioCallbacks,
  type PortfolioOverviewData,
} from "./PortfolioSections";
import { createHeatmap } from "./Heatmap";
import { createTimelineScrubber } from "./TimelineScrubber";
import { createAccountsPanel, type ExchangeRegistryEntry } from "./AccountsPanel";
import { createArbitragePanel } from "./ArbitragePanel";
import { createComparisonsPanel } from "./ComparisonsPanel";
import { createGoalsPanel } from "./GoalsPanel";
import { createRebalancePanel } from "./RebalancePanel";
import { createTagsPanel } from "./tags/TagsPanel";
import { createPlatformPanel, type PlatformData } from "../platform/PlatformPanel";

export type PortfolioPanelState = {
  overview: PortfolioOverviewData | null;
  equityCurve: EquityPoint[];
  snapshotDates: string[];
  heatmap: Array<{ asset: string; return_pct: number; volatility_pct: number }>;
  selectedDate: string | null;
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
};

export function createPortfolioPanel(
  state: PortfolioPanelState,
  callbacks: PortfolioCallbacks & {
    onScrubDate: (date: string) => void;
    onTagFilter: (tag: string | null) => void;
    onRebalanceApply: () => void;
    onSyncAll: () => void;
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

  const holdings =
    state.tagFilter
      ? state.overview.holdings.filter((h) => (h.tag as string | undefined) === state.tagFilter)
      : state.overview.holdings;

  root.appendChild(createPortfolioHero(state.overview));
  root.appendChild(createQuickActions(callbacks));

  const syncAllBtn = document.createElement("button");
  syncAllBtn.type = "button";
  syncAllBtn.className = "gp-btn-secondary";
  syncAllBtn.dataset.testid = "portfolio-sync-all";
  syncAllBtn.textContent = t("portfolio.sync_all");
  syncAllBtn.addEventListener("click", () => callbacks.onSyncAll());
  root.appendChild(syncAllBtn);

  if (state.overview.accounts?.length) {
    root.appendChild(createAccountsPanel(state.overview.accounts, state.exchangeRegistry));
  }

  const chartMount = document.createElement("div");
  chartMount.className = "gp-chart-mount";
  chartMount.dataset.testid = "portfolio-equity-chart";
  root.appendChild(chartMount);
  if (state.equityCurve.length) {
    chartCleanup = renderEquityChart(chartMount, state.equityCurve);
  }

  if (state.snapshotDates.length) {
    root.appendChild(
      createTimelineScrubber(state.snapshotDates, state.selectedDate, callbacks.onScrubDate),
    );
  }

  root.appendChild(
    createTagsPanel(
      state.overview.holdings as Array<{ asset: string; tag?: string }>,
      callbacks.onTagFilter,
    ),
  );
  root.appendChild(createGoalsPanel(state.overview.performance_goal ?? null));
  if (state.overview.comparisons?.length) {
    root.appendChild(createComparisonsPanel(state.overview.comparisons));
  }
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

  root.appendChild(createHoldingsTable(holdings));
  root.appendChild(createAllocationSection(state.overview.allocation));
  root.appendChild(createPlBreakdown(state.overview.pl_breakdown));
  root.appendChild(createPeriodComparison(state.overview.periods));
  root.appendChild(createHeatmap(state.heatmap));
  root.appendChild(createBotUnifiedSection(state.overview.bot));
  if (state.platform) {
    root.appendChild(createPlatformPanel(state.platform));
  }

  return {
    root,
    cleanup: () => chartCleanup(),
  };
}
