import type { BacktestRanking } from "../api/client";
import { formatUsd } from "../portfolio/formatUsd";
import { t } from "../i18n";

export function createBacktestTop5Bar(
  rankings: BacktestRanking[],
  onApply: (ranking: BacktestRanking) => void,
): HTMLElement | null {
  if (!rankings.length) return null;
  const bar = document.createElement("div");
  bar.className = "gp-backtest-top5";
  bar.dataset.testid = "bot-backtest-top5";
  bar.innerHTML = `<h3 class="gp-panel-subtitle">${t("bots.detail.backtest_top5")}</h3>`;
  const row = document.createElement("div");
  row.className = "gp-backtest-top5-row";
  for (const [idx, rank] of rankings.slice(0, 5).entries()) {
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "gp-btn-secondary gp-backtest-top5-btn";
    btn.dataset.testid = `backtest-apply-${idx}`;
    const id = String(rank.indicator ?? rank.ta_function ?? rank.id ?? rank.fn ?? `#${idx + 1}`);
    btn.textContent = `${idx + 1}. ${id} (${formatUsd(Number(rank.profit_total ?? 0), { signed: true })})`;
    btn.addEventListener("click", () => onApply(rank));
    row.appendChild(btn);
  }
  bar.appendChild(row);
  return bar;
}
