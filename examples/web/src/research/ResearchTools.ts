import { t } from "../i18n";
import { renderHeatmapChart } from "./researchHeatmap";

export type ResearchCallbacks = {
  onWalkForward: () => void;
  onMonteCarlo: () => void;
  onPortfolioMc: () => void;
  onHeatmap: () => void;
};

type ToolDef = {
  id: string;
  labelKey: string;
  hintKey: string;
  testId?: string;
  onClick: () => void;
};

function toolButton(def: ToolDef): HTMLElement {
  const wrap = document.createElement("div");
  wrap.className = "gp-research-tool";
  const btn = document.createElement("button");
  btn.type = "button";
  btn.className = "gp-btn-secondary";
  if (def.testId) btn.dataset.testid = def.testId;
  btn.textContent = t(def.labelKey);
  btn.title = t(def.hintKey);
  btn.setAttribute("aria-describedby", `${def.id}-hint`);
  btn.addEventListener("click", () => def.onClick());
  const hint = document.createElement("p");
  hint.id = `${def.id}-hint`;
  hint.className = "gp-body gp-muted gp-research-hint";
  hint.textContent = t(def.hintKey);
  wrap.append(btn, hint);
  return wrap;
}

export function createResearchToolsPanel(
  results: Record<string, unknown>,
  callbacks: ResearchCallbacks,
): HTMLElement {
  const section = document.createElement("section");
  section.className = "gp-panel";
  section.dataset.testid = "research-tools";
  section.innerHTML = `<h3>${t("research.tools")}</h3><p class="gp-body gp-muted">${t("research.tools_intro")}</p>`;

  const actions = document.createElement("div");
  actions.className = "gp-research-tools-grid";
  const tools: ToolDef[] = [
    {
      id: "wf",
      labelKey: "research.walk_forward",
      hintKey: "research.walk_forward_hint",
      testId: "walk-forward",
      onClick: () => callbacks.onWalkForward(),
    },
    {
      id: "mc",
      labelKey: "research.monte_carlo",
      hintKey: "research.monte_carlo_hint",
      testId: "monte-carlo",
      onClick: () => callbacks.onMonteCarlo(),
    },
    {
      id: "pmc",
      labelKey: "research.portfolio_mc",
      hintKey: "research.portfolio_mc_hint",
      onClick: () => callbacks.onPortfolioMc(),
    },
    {
      id: "hm",
      labelKey: "research.heatmap",
      hintKey: "research.heatmap_hint",
      testId: "hyperopt-heatmap",
      onClick: () => callbacks.onHeatmap(),
    },
  ];
  for (const def of tools) {
    actions.appendChild(toolButton(def));
  }
  section.appendChild(actions);

  if (results.error) {
    const err = document.createElement("p");
    err.className = "gp-error-banner";
    err.dataset.testid = "research-error";
    err.setAttribute("role", "alert");
    err.textContent = String(results.error);
    section.appendChild(err);
    return section;
  }

  const keys = Object.keys(results).filter((k) => k !== "loading");
  if (!keys.length) {
    if (results.loading) {
      const loading = document.createElement("p");
      loading.dataset.testid = "research-loading";
      loading.textContent = t("research.running");
      section.appendChild(loading);
    } else {
      const empty = document.createElement("p");
      empty.className = "gp-empty";
      empty.dataset.testid = "research-empty";
      empty.textContent = t("empty.research");
      section.appendChild(empty);
    }
    return section;
  }

  const heatmap = results.heatmap as { matrix?: number[][]; assets?: string[] } | undefined;
  if (heatmap?.matrix?.length && heatmap.assets?.length) {
    section.appendChild(renderHeatmapChart(heatmap.matrix, heatmap.assets));
  }

  const pre = document.createElement("pre");
  pre.className = "gp-research-output";
  pre.dataset.testid = "research-output";
  pre.textContent = JSON.stringify(results, null, 2);
  section.appendChild(pre);
  return section;
}
