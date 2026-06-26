import { t } from "../i18n";

export type Recommendation = {
  strategy_id: string;
  score: number;
  reasons: string[];
  requires_backtest: boolean;
};

export function createRecommenderPanel(
  recommendations: Recommendation[],
  disclaimer: string,
  onDeploy: (id: string) => void,
): HTMLElement {
  const section = document.createElement("section");
  section.className = "gp-panel";
  section.dataset.testid = "ai-recommender";
  section.innerHTML = `<h3>${t("ai.recommender")}</h3><p class="gp-disclaimer">${disclaimer}</p>`;
  const list = document.createElement("ul");
  for (const rec of recommendations.slice(0, 5)) {
    const li = document.createElement("li");
    li.innerHTML = `<strong>${rec.strategy_id}</strong> (${rec.score}) — ${rec.reasons.join("; ")}`;
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "gp-btn-secondary";
    btn.textContent = t("strategies.deploy");
    btn.addEventListener("click", () => onDeploy(rec.strategy_id));
    li.appendChild(btn);
    list.appendChild(li);
  }
  section.appendChild(list);
  return section;
}
