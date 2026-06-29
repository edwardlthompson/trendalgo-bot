import type { FleetResultRow } from "../api/client";
import { formatUsd } from "../portfolio/formatUsd";
import { t } from "../i18n";
import {
  filterBeatsBuyHold,
  formatNetProfitPct,
  formatVsBuyHoldPct,
  strategyOptimizedMarker,
  vsBuyHoldAmount,
} from "./fleetResults";

function formatPct(rate: number): string {
  return `${(rate * 100).toFixed(0)}%`;
}

function paramsLabel(params: Record<string, unknown> | undefined): string {
  if (!params || !Object.keys(params).length) return "—";
  return Object.entries(params)
    .map(([k, v]) => `${k}=${String(v)}`)
    .join(", ");
}

function tslHitsLabel(row: FleetResultRow): string {
  if (row.tsl_hits == null) return "—";
  return String(row.tsl_hits);
}

function tslLabel(row: FleetResultRow): string {
  const pct = row.optimal_tsl_pct ?? row.trailing_stop_pct ?? 0;
  return formatPct(Number(pct));
}

export function renderResultsTable(
  rows: FleetResultRow[],
  title: string,
  stakeUsd: number,
  options?: {
    deploy?: (row: FleetResultRow, index: number) => void;
    buyHold?: FleetResultRow;
    onOpenGlossaryStrategy?: (strategyId: string) => void;
  },
): HTMLElement {
  const buyHold = options?.buyHold;
  const bhNet = buyHold?.net_profit != null ? Number(buyHold.net_profit) : null;
  const strategyRows = filterBeatsBuyHold(rows, bhNet);
  const showBhCols = bhNet != null;

  const wrap = document.createElement("div");
  wrap.className = "gp-fleet-results-block";
  wrap.innerHTML = `<h3 class="gp-panel-subtitle">${title}</h3>`;
  if (showBhCols && !strategyRows.length) {
    const hint = document.createElement("p");
    hint.className = "gp-body gp-muted";
    hint.textContent = t("backtest.empty_beats_bh");
    wrap.appendChild(hint);
  }
  const table = document.createElement("table");
  table.className = "gp-data-table gp-fleet-results-table";
  const actionHeader = options?.deploy ? `<th>${t("backtest.col.action")}</th>` : "";
  table.innerHTML = `<thead><tr>
    <th>${t("backtest.col.rank")}</th>
    <th>${t("backtest.col.strategy")}</th>
    <th>${t("backtest.col.timeframe")}</th>
    <th>${t("backtest.col.net")}</th>
    <th>${t("backtest.col.net_pct")}</th>
    ${showBhCols ? `<th>${t("backtest.col.vs_bh")}</th><th>${t("backtest.col.vs_bh_pct")}</th>` : ""}
    <th>${t("backtest.col.trades")}</th>
    <th>${t("backtest.col.tsl")}</th>
    <th>${t("backtest.col.tsl_hits")}</th>
    <th>${t("backtest.col.params")}</th>
    ${actionHeader}
  </tr></thead>`;
  const tbody = document.createElement("tbody");

  if (buyHold && bhNet != null) {
    const tr = document.createElement("tr");
    tr.className = "gp-fleet-baseline-row";
    tr.dataset.testid = "backtest-buy-hold-row";
    tr.innerHTML = `
      <td>—</td>
      <td>${t("backtest.buy_hold")}</td>
      <td>${buyHold.timeframe ?? "—"}</td>
      <td>${formatUsd(bhNet, { signed: true })}</td>
      <td>${formatNetProfitPct(bhNet, stakeUsd)}</td>
      <td>${t("backtest.vs_bh_baseline")}</td>
      <td>${t("backtest.vs_bh_baseline")}</td>
      <td>${buyHold.trades ?? 1}</td>
      <td>—</td>
      <td>—</td>
      <td>—</td>
    `;
    tbody.appendChild(tr);
  }

  for (const [idx, row] of strategyRows.entries()) {
    const tr = document.createElement("tr");
    tr.appendChild(Object.assign(document.createElement("td"), { textContent: String(row.rank ?? idx + 1) }));

    const strategyCell = document.createElement("td");
    if (options?.onOpenGlossaryStrategy) {
      const link = document.createElement("button");
      link.type = "button";
      link.className = "gp-ta-glossary-link gp-backtest-strategy-link";
      link.dataset.testid = `backtest-strategy-link-${row.strategy_id}`;
      link.textContent = row.strategy_id;
      link.addEventListener("click", () => options.onOpenGlossaryStrategy!(row.strategy_id));
      strategyCell.appendChild(link);
    } else {
      strategyCell.textContent = row.strategy_id;
    }
    if (strategyOptimizedMarker(row)) {
      const mark = document.createElement("span");
      mark.className = "gp-backtest-optimized-mark";
      mark.textContent = " *";
      mark.title = t("backtest.optimized_mark_hint");
      mark.setAttribute("aria-label", t("backtest.optimized_mark_hint"));
      strategyCell.appendChild(mark);
    }
    tr.appendChild(strategyCell);

    tr.appendChild(Object.assign(document.createElement("td"), { textContent: row.timeframe }));
    tr.appendChild(
      Object.assign(document.createElement("td"), {
        textContent: formatUsd(row.net_profit, { signed: true }),
      }),
    );
    tr.appendChild(
      Object.assign(document.createElement("td"), {
        textContent: formatNetProfitPct(Number(row.net_profit), stakeUsd),
      }),
    );
    if (showBhCols && bhNet != null) {
      tr.appendChild(
        Object.assign(document.createElement("td"), {
          textContent: formatUsd(vsBuyHoldAmount(Number(row.net_profit), bhNet), { signed: true }),
        }),
      );
      tr.appendChild(
        Object.assign(document.createElement("td"), {
          textContent: formatVsBuyHoldPct(Number(row.net_profit), bhNet, stakeUsd),
        }),
      );
    }
    tr.appendChild(Object.assign(document.createElement("td"), { textContent: String(row.trades) }));
    tr.appendChild(Object.assign(document.createElement("td"), { textContent: tslLabel(row) }));
    tr.appendChild(Object.assign(document.createElement("td"), { textContent: tslHitsLabel(row) }));
    const paramsCell = document.createElement("td");
    paramsCell.innerHTML = `<code class="gp-params-cell">${paramsLabel(row.params as Record<string, unknown>)}</code>`;
    tr.appendChild(paramsCell);

    if (options?.deploy) {
      const actionCell = document.createElement("td");
      const btn = document.createElement("button");
      btn.type = "button";
      btn.className = "gp-btn-secondary gp-backtest-create-bot";
      btn.dataset.testid = `backtest-create-bot-${idx}`;
      btn.textContent = t("backtest.create_bot");
      btn.addEventListener("click", () => options.deploy!(row, idx));
      actionCell.appendChild(btn);
      tr.appendChild(actionCell);
    }
    tbody.appendChild(tr);
  }
  table.appendChild(tbody);
  wrap.appendChild(table);
  if (strategyRows.some(strategyOptimizedMarker)) {
    wrap.appendChild(
      Object.assign(document.createElement("p"), {
        className: "gp-body gp-muted gp-fleet-results-legend",
        textContent: t("backtest.optimized_legend"),
      }),
    );
  }
  return wrap;
}
