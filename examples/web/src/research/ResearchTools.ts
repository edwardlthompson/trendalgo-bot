import { t } from "../i18n";

export type ResearchCallbacks = {
  onWalkForward: () => void;
  onMonteCarlo: () => void;
  onPortfolioMc: () => void;
  onHeatmap: () => void;
};

export function createResearchToolsPanel(
  results: Record<string, unknown>,
  callbacks: ResearchCallbacks,
): HTMLElement {
  const section = document.createElement("section");
  section.className = "gp-panel";
  section.dataset.testid = "research-tools";
  section.innerHTML = `<h3>${t("research.tools")}</h3>`;
  const actions = document.createElement("div");
  actions.className = "gp-panel-actions";
  const wf = document.createElement("button");
  wf.type = "button";
  wf.className = "gp-btn-secondary";
  wf.dataset.testid = "walk-forward";
  wf.textContent = t("research.walk_forward");
  wf.addEventListener("click", () => callbacks.onWalkForward());
  const mc = document.createElement("button");
  mc.type = "button";
  mc.className = "gp-btn-secondary";
  mc.dataset.testid = "monte-carlo";
  mc.textContent = t("research.monte_carlo");
  mc.addEventListener("click", () => callbacks.onMonteCarlo());
  const pmc = document.createElement("button");
  pmc.type = "button";
  pmc.className = "gp-btn-secondary";
  pmc.textContent = t("research.portfolio_mc");
  pmc.addEventListener("click", () => callbacks.onPortfolioMc());
  const hm = document.createElement("button");
  hm.type = "button";
  hm.className = "gp-btn-secondary";
  hm.dataset.testid = "hyperopt-heatmap";
  hm.textContent = t("research.heatmap");
  hm.addEventListener("click", () => callbacks.onHeatmap());
  actions.append(wf, mc, pmc, hm);
  section.appendChild(actions);
  const pre = document.createElement("pre");
  pre.className = "gp-research-output";
  pre.dataset.testid = "research-output";
  pre.textContent = JSON.stringify(results, null, 2);
  section.appendChild(pre);
  return section;
}
