import { t } from "../i18n";

export type RiskPanelCallbacks = {
  onPause: () => void;
  onResume: () => void;
};

export function createRiskPanel(
  risk: Record<string, string | number | boolean>,
  callbacks: RiskPanelCallbacks,
): HTMLElement {
  const section = document.createElement("section");
  section.className = "gp-panel";
  section.dataset.testid = "risk-panel";
  const paused = Boolean(risk.paused);
  section.innerHTML = `
    <h2 class="gp-panel-title">${t("risk.title")}</h2>
    <dl class="gp-stat-grid">
      <div><dt>${t("health.equity")}</dt><dd>$${Number(risk.equity_usd ?? 0).toFixed(2)}</dd></div>
      <div><dt>${t("risk.daily_pnl")}</dt><dd>$${Number(risk.daily_pnl_usd ?? 0).toFixed(2)}</dd></div>
      <div><dt>${t("health.drawdown")}</dt><dd>${(Number(risk.drawdown_pct ?? 0) * 100).toFixed(1)}%</dd></div>
      <div><dt>${t("risk.can_trade")}</dt><dd>${risk.can_trade ? t("risk.yes") : t("risk.no")}</dd></div>
    </dl>
  `;
  const actions = document.createElement("div");
  actions.className = "gp-panel-actions";
  const pauseBtn = document.createElement("button");
  pauseBtn.type = "button";
  pauseBtn.className = "gp-btn-danger";
  pauseBtn.textContent = t("risk.pause_all");
  pauseBtn.dataset.testid = "pause-all";
  pauseBtn.disabled = paused;
  pauseBtn.addEventListener("click", () => callbacks.onPause());
  const resumeBtn = document.createElement("button");
  resumeBtn.type = "button";
  resumeBtn.className = "gp-btn-primary";
  resumeBtn.textContent = t("risk.resume");
  resumeBtn.dataset.testid = "resume-trading";
  resumeBtn.disabled = !paused;
  resumeBtn.addEventListener("click", () => callbacks.onResume());
  actions.append(pauseBtn, resumeBtn);
  section.appendChild(actions);
  return section;
}
