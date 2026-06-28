import {
  renderPerformanceComparisonChart,
  type EquityPoint,
  type PerformanceComparison,
} from "../charts/EquityChart";
import { t } from "../i18n";

export type PerformanceRange = "1y" | "6m" | "3m" | "1m" | "14d" | "7d" | "24h";

export const PERFORMANCE_RANGES: PerformanceRange[] = [
  "1y",
  "6m",
  "3m",
  "1m",
  "14d",
  "7d",
  "24h",
];

export function createPortfolioPerformanceChart(
  points: EquityPoint[],
  benchmark: EquityPoint[],
  comparison: PerformanceComparison | null,
  activeRange: PerformanceRange,
  onRangeChange: (range: PerformanceRange) => void,
): { root: HTMLElement; cleanup: () => void } {
  const section = document.createElement("section");
  section.className = "gp-panel gp-performance-panel";
  section.dataset.testid = "portfolio-performance-panel";

  const header = document.createElement("div");
  header.className = "gp-panel-header";
  header.innerHTML = `<h2 class="gp-panel-title">${t("portfolio.performance")}</h2>`;
  section.appendChild(header);

  if (comparison) {
    const stats = document.createElement("p");
    stats.className = "gp-performance-stats";
    stats.dataset.testid = "portfolio-top10-comparison";
    const alphaSign = comparison.alpha_pct >= 0 ? "+" : "";
    stats.textContent = `${t("portfolio.legend.portfolio")} ${comparison.portfolio_return_pct.toFixed(2)}% · ${t("portfolio.legend.top10")} ${comparison.top10_return_pct.toFixed(2)}% · α ${alphaSign}${comparison.alpha_pct.toFixed(2)}%`;
    section.appendChild(stats);
  }

  const ranges = document.createElement("div");
  ranges.className = "gp-performance-ranges";
  ranges.setAttribute("role", "tablist");
  ranges.setAttribute("aria-label", t("portfolio.performance_ranges"));

  for (const range of PERFORMANCE_RANGES) {
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "gp-btn-secondary gp-range-btn";
    btn.dataset.range = range;
    btn.dataset.testid = `performance-range-${range}`;
    btn.setAttribute("role", "tab");
    btn.setAttribute("aria-selected", activeRange === range ? "true" : "false");
    btn.textContent = t(`portfolio.range.${range}`);
    if (activeRange === range) {
      btn.classList.add("gp-range-btn-active");
    }
    btn.addEventListener("click", () => {
      if (range !== activeRange) onRangeChange(range);
    });
    ranges.appendChild(btn);
  }
  section.appendChild(ranges);

  const legend = document.createElement("div");
  legend.className = "gp-chart-legend";
  legend.dataset.testid = "portfolio-chart-legend";
  legend.innerHTML = `
    <span class="gp-legend-item gp-legend-portfolio">${t("portfolio.legend.portfolio")}</span>
    <span class="gp-legend-item gp-legend-top10">${t("portfolio.legend.top10")}</span>
  `;
  section.appendChild(legend);

  const chartMount = document.createElement("div");
  chartMount.className = "gp-chart-host";
  chartMount.dataset.testid = "portfolio-equity-chart";
  section.appendChild(chartMount);

  let chartCleanup = (): void => {};
  if (points.length) {
    chartCleanup = renderPerformanceComparisonChart(chartMount, points, benchmark).cleanup;
  } else {
    chartMount.textContent = t("portfolio.performance_empty");
  }

  return {
    root: section,
    cleanup: () => chartCleanup(),
  };
}
