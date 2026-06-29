import type { FleetHistoryEntry } from "../api/client";
import { formatUsd } from "../portfolio/formatUsd";
import { t } from "../i18n";

function formatTimeframes(timeframes: string[] | undefined): string {
  if (!timeframes?.length) return "—";
  return timeframes.join(", ");
}

export function createFleetHistoryPanel(
  runs: FleetHistoryEntry[],
  selectedJobId: string | null,
  onSelect: (jobId: string) => void,
): HTMLElement {
  const section = document.createElement("section");
  section.className = "gp-panel gp-fleet-history";
  section.dataset.testid = "backtest-fleet-history";
  const title =
    runs.length > 0
      ? `${t("backtest.history.title")} (${runs.length})`
      : t("backtest.history.title");
  section.innerHTML = `<h3 class="gp-panel-subtitle">${title}</h3>`;
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
    li.className = "gp-fleet-history-item";
    const card = document.createElement("button");
    card.type = "button";
    card.className =
      selectedJobId === run.job_id
        ? "gp-fleet-history-card gp-fleet-history-card-selected"
        : "gp-fleet-history-card";
    card.dataset.testid = `fleet-history-${run.job_id}`;
    card.title = t("backtest.history.load_hint");

    const when = run.created_at ? new Date(run.created_at).toLocaleString() : run.job_id;
    const head = document.createElement("div");
    head.className = "gp-fleet-history-head";
    head.innerHTML = `<strong>${when}</strong> · ${run.exchange_id} ${run.pair} · ${formatUsd(run.stake_usd)}`;
    card.appendChild(head);

    const meta = document.createElement("dl");
    meta.className = "gp-fleet-history-meta";
    const bestNet =
      run.best_net_profit != null ? formatUsd(run.best_net_profit, { signed: true }) : "—";
    const buyHold =
      run.buy_hold_net != null ? formatUsd(run.buy_hold_net, { signed: true }) : "—";
    meta.innerHTML = `
      <div><dt>${t("backtest.history.lookback")}</dt><dd>${run.lookback_days ?? 30}d</dd></div>
      <div><dt>${t("backtest.history.timeframes")}</dt><dd>${formatTimeframes(run.timeframes_tested)}</dd></div>
      <div><dt>${t("backtest.history.best")}</dt><dd>${run.best_strategy ?? "—"} @ ${run.best_timeframe ?? "—"} (${bestNet})</dd></div>
      <div><dt>${t("backtest.buy_hold")}</dt><dd>${buyHold}</dd></div>
      <div><dt>${t("backtest.history.top10")}</dt><dd>${run.top10_count ?? 0}</dd></div>
    `;
    card.appendChild(meta);
    card.addEventListener("click", () => onSelect(run.job_id));
    li.appendChild(card);
    list.appendChild(li);
  }
  section.appendChild(list);
  return section;
}
