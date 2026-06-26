import { t } from "../i18n";

export type RebalanceSuggestion = {
  asset: string;
  current_pct: number;
  target_pct: number;
  delta_usd: number;
  action: string;
};

export function createRebalancePanel(
  suggestions: RebalanceSuggestion[],
  onApply: () => void,
): HTMLElement {
  const section = document.createElement("section");
  section.className = "gp-panel";
  section.dataset.testid = "portfolio-rebalance";
  section.innerHTML = `<h3>${t("portfolio.rebalance")}</h3><p class="gp-disclaimer">${t("portfolio.rebalance_disclaimer")}</p>`;
  const list = document.createElement("ul");
  for (const s of suggestions.slice(0, 5)) {
    const li = document.createElement("li");
    li.textContent = `${s.action.toUpperCase()} ${s.asset}: $${Math.abs(s.delta_usd).toFixed(2)} (${(s.current_pct * 100).toFixed(1)}% → ${(s.target_pct * 100).toFixed(1)}%)`;
    list.appendChild(li);
  }
  section.appendChild(list);
  const btn = document.createElement("button");
  btn.type = "button";
  btn.className = "gp-btn-secondary";
  btn.dataset.testid = "rebalance-apply";
  btn.textContent = t("portfolio.rebalance_apply");
  btn.addEventListener("click", onApply);
  section.appendChild(btn);
  return section;
}
