import { t } from "../i18n";

export type GoalData = {
  label: string;
  target_net_worth_usd: number;
  progress_pct: number;
  remaining_usd: number;
  current_net_worth_usd: number;
};

export function createGoalsPanel(goal: GoalData | null): HTMLElement {
  const section = document.createElement("section");
  section.className = "gp-panel";
  section.dataset.testid = "portfolio-goals";
  section.innerHTML = `<h3>${t("portfolio.goals")}</h3>`;
  if (!goal) {
    section.innerHTML += `<p>${t("portfolio.goals_empty")}</p>`;
    return section;
  }
  const bar = document.createElement("div");
  bar.className = "gp-progress-bar";
  bar.dataset.testid = "goal-progress";
  const fill = document.createElement("div");
  fill.className = "gp-progress-fill";
  fill.style.width = `${Math.min(100, goal.progress_pct * 100)}%`;
  bar.appendChild(fill);
  const meta = document.createElement("p");
  meta.className = "gp-body";
  meta.textContent = `${goal.label}: $${goal.current_net_worth_usd.toFixed(2)} / $${goal.target_net_worth_usd.toFixed(2)} (${(goal.progress_pct * 100).toFixed(1)}%)`;
  section.append(bar, meta);
  return section;
}
