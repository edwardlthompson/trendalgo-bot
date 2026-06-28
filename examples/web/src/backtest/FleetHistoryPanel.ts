import type { FleetHistoryEntry } from "../api/client";
import { formatUsd } from "../portfolio/formatUsd";
import { t } from "../i18n";

export function createFleetHistoryPanel(
  runs: FleetHistoryEntry[],
  selectedJobId: string | null,
  onSelect: (jobId: string) => void,
): HTMLElement {
  const section = document.createElement("section");
  section.className = "gp-panel gp-fleet-history";
  section.dataset.testid = "backtest-fleet-history";
  section.innerHTML = `<h3 class="gp-panel-subtitle">${t("backtest.history.title")}</h3>`;
  if (!runs.length) {
    const empty = document.createElement("p");
    empty.className = "gp-body gp-muted";
    empty.textContent = t("backtest.history.empty");
    section.appendChild(empty);
    return section;
  }
  const list = document.createElement("ul");
  list.className = "gp-fleet-history-list";
  for (const run of runs) {
    const li = document.createElement("li");
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = selectedJobId === run.job_id ? "gp-btn-primary" : "gp-btn-secondary";
    btn.dataset.testid = `fleet-history-${run.job_id}`;
    const when = run.created_at ? new Date(run.created_at).toLocaleString() : run.job_id;
    const best = run.best_net_profit != null ? formatUsd(run.best_net_profit, { signed: true }) : "—";
    btn.textContent = `${when} · ${run.exchange_id} ${run.pair} · best ${best}`;
    btn.title = t("backtest.history.load_hint");
    btn.addEventListener("click", () => onSelect(run.job_id));
    li.appendChild(btn);
    list.appendChild(li);
  }
  section.appendChild(list);
  return section;
}
