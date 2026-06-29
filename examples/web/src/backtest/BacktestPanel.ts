import type {
  ExchangeFeeSchedule,
  FleetActiveSnapshot,
  FleetHistoryEntry,
  FleetLatestPayload,
  FleetResultRow,
} from "../api/client";
import type { ExchangeRegistryEntry } from "../portfolio/AccountsPanel";
import { createFleetHistoryPanel } from "./FleetHistoryPanel";
import {
  buyHoldFromSummary,
  buyHoldNet,
  filterBeatsBuyHold,
  formatNetProfitPct,
  formatVsBuyHoldPct,
  strategyOptimizedMarker,
  vsBuyHoldAmount,
} from "./fleetResults";
import { formatUsd } from "../portfolio/formatUsd";
import { t } from "../i18n";

export type FleetFilterMode = "all" | "timeframe" | "strategy";

export type BacktestPanelProps = {
  loading: boolean;
  exchangeId: string;
  pair: string;
  stakeUsd: number;
  exchanges: ExchangeRegistryEntry[];
  pairs: string[];
  feeSchedule: ExchangeFeeSchedule | null;
  active: FleetActiveSnapshot | null;
  results: FleetLatestPayload | null;
  historyRuns: FleetHistoryEntry[];
  selectedHistoryJobId: string | null;
  filterMode: FleetFilterMode;
  filterTimeframe: string;
};

export type BacktestPanelCallbacks = {
  onRun: () => void;
  onExchangeChange: (exchangeId: string) => void;
  onPairChange: (pair: string) => void;
  onStakeChange: (stakeUsd: number) => void;
  onFilterChange: (mode: FleetFilterMode, timeframe?: string) => void;
  onLoadHistoryRun: (jobId: string) => void;
  onCreateBotFromResult?: (row: FleetResultRow) => void;
  onOpenGlossaryStrategy?: (strategyId: string) => void;
};

function formatPct(rate: number): string {
  return `${(rate * 100).toFixed(0)}%`;
}

function formatDuration(seconds: number | null | undefined): string {
  if (seconds == null || seconds < 0) return "—";
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  const s = seconds % 60;
  if (h > 0) return `${h}h ${m}m ${s}s`;
  if (m > 0) return `${m}m ${s}s`;
  return `${s}s`;
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

function phaseLabel(phase: string | undefined): string {
  if (phase === "optimize_params") return t("backtest.phase.optimize");
  if (phase === "optimize_tsl") return t("backtest.phase.optimize_tsl");
  return t("backtest.phase.pass1");
}

function renderResultsTable(
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

export function createBacktestPanel(
  props: BacktestPanelProps,
  callbacks: BacktestPanelCallbacks,
): { root: HTMLElement; cleanup: () => void } {
  const root = document.createElement("section");
  root.className = "gp-panel";
  root.dataset.testid = "backtest-panel";

  const header = document.createElement("div");
  header.className = "gp-panel-header";
  header.innerHTML = `<h2 class="gp-panel-title">${t("backtest.title")}</h2>`;
  const runBtn = document.createElement("button");
  runBtn.type = "button";
  runBtn.className = "gp-btn-primary";
  runBtn.textContent = props.loading ? t("backtest.running") : t("backtest.run");
  runBtn.disabled = props.loading;
  runBtn.dataset.testid = "backtest-run";
  runBtn.addEventListener("click", () => callbacks.onRun());
  header.appendChild(runBtn);
  root.appendChild(header);

  const form = document.createElement("div");
  form.className = "gp-form-grid";
  form.dataset.testid = "backtest-fleet-form";

  const exchangeLabel = document.createElement("label");
  exchangeLabel.textContent = t("backtest.exchange");
  const exchangeSelect = document.createElement("select");
  exchangeSelect.dataset.testid = "backtest-exchange";
  const registry = props.exchanges.length
    ? props.exchanges
    : [{ id: "kraken", brand: "Kraken", tier: "1", portfolio_enabled: true, trading_enabled: true }];
  for (const ex of registry) {
    const opt = document.createElement("option");
    opt.value = ex.id;
    opt.textContent = ex.brand;
    opt.selected = ex.id === props.exchangeId;
    exchangeSelect.appendChild(opt);
  }
  exchangeSelect.addEventListener("change", () => callbacks.onExchangeChange(exchangeSelect.value));
  exchangeLabel.appendChild(exchangeSelect);
  form.appendChild(exchangeLabel);

  const pairLabel = document.createElement("label");
  pairLabel.textContent = t("backtest.pair");
  const pairSelect = document.createElement("select");
  pairSelect.dataset.testid = "backtest-pair";
  for (const p of props.pairs) {
    const opt = document.createElement("option");
    opt.value = p;
    opt.textContent = p;
    opt.selected = p === props.pair;
    pairSelect.appendChild(opt);
  }
  pairSelect.addEventListener("change", () => callbacks.onPairChange(pairSelect.value));
  pairLabel.appendChild(pairSelect);
  form.appendChild(pairLabel);

  const stakeLabel = document.createElement("label");
  stakeLabel.textContent = t("backtest.stake");
  const stakeInput = document.createElement("input");
  stakeInput.type = "number";
  stakeInput.min = "1";
  stakeInput.step = "100";
  stakeInput.value = String(props.stakeUsd);
  stakeInput.dataset.testid = "backtest-stake";
  stakeInput.addEventListener("change", () => {
    const val = Number(stakeInput.value);
    if (Number.isFinite(val) && val > 0) callbacks.onStakeChange(val);
  });
  stakeLabel.appendChild(stakeInput);
  form.appendChild(stakeLabel);
  root.appendChild(form);

  const feeLine = document.createElement("p");
  feeLine.className = "gp-body gp-muted";
  feeLine.dataset.testid = "backtest-fee-line";
  const fee = props.feeSchedule;
  if (fee) {
    feeLine.textContent = `${t("backtest.fees")}: ${fee.exchange_id} ${t("backtest.taker")} ${(fee.taker_pct * 100).toFixed(2)}% (${t("backtest.retail_default")})`;
  } else {
    feeLine.textContent = t("backtest.fee_loading");
  }
  root.appendChild(feeLine);

  root.appendChild(Object.assign(document.createElement("p"), {
    className: "gp-body gp-muted",
    textContent: t("backtest.uniform_window_hint"),
  }));

  root.appendChild(Object.assign(document.createElement("p"), {
    className: "gp-body gp-muted",
    textContent: t("backtest.tsl_auto_hint"),
  }));

  root.appendChild(
    createFleetHistoryPanel(props.historyRuns, props.selectedHistoryJobId, (jobId) =>
      callbacks.onLoadHistoryRun(jobId),
    ),
  );

  const active = props.active;
  if (props.loading || active?.status === "running") {
    const progressWrap = document.createElement("div");
    progressWrap.dataset.testid = "backtest-fleet-progress";
    const pct = active?.progress_pct ?? 0;
    progressWrap.innerHTML = `
      <div class="gp-progress-bar" role="progressbar" aria-valuenow="${pct}">
        <div class="gp-progress-fill" style="width:${pct}%"></div>
      </div>
      <p class="gp-body"><strong>${phaseLabel(active?.phase)}</strong> · ${pct}% · ${active?.completed ?? 0}/${active?.total_combinations ?? 0}</p>
      <p class="gp-body">${t("backtest.elapsed")}: ${formatDuration(active?.elapsed_seconds)} · ${t("backtest.eta")}: ${formatDuration(active?.eta_seconds ?? null)}</p>
      <p class="gp-body gp-muted">${t("backtest.current")}: ${active?.current_test || "—"}</p>
    `;
    root.appendChild(progressWrap);

    if (active?.recent_tests?.length) {
      const testLog = document.createElement("div");
      testLog.className = "gp-fleet-test-log";
      testLog.dataset.testid = "backtest-fleet-test-log";
      testLog.innerHTML = `<h4 class="gp-panel-subtitle">${t("backtest.test_log")}</h4>`;
      const list = document.createElement("ul");
      list.className = "gp-log-list";
      for (const entry of [...active.recent_tests].reverse().slice(0, 20)) {
        const li = document.createElement("li");
        const net =
          entry.net_profit != null ? formatUsd(Number(entry.net_profit), { signed: true }) : entry.status;
        li.textContent = `[${entry.phase ?? "pass1"}] ${entry.strategy_id} @ ${entry.timeframe} → ${net}`;
        list.appendChild(li);
      }
      testLog.appendChild(list);
      root.appendChild(testLog);
    }

    if (active?.messages?.length) {
      const log = document.createElement("ul");
      log.className = "gp-log-list gp-fleet-verbose-log";
      log.dataset.testid = "backtest-fleet-messages";
      for (const msg of active.messages.slice(-12)) {
        const li = document.createElement("li");
        li.textContent = msg;
        log.appendChild(li);
      }
      root.appendChild(log);
    }
  }

  const summary = props.results?.summary ?? active?.summary;
  const buyHold = buyHoldFromSummary(summary as Record<string, unknown> | undefined);
  const bhNet = buyHoldNet(summary as Record<string, unknown> | undefined);

  const finalTopRaw =
    (summary?.final_top10 as FleetResultRow[] | undefined) ??
    (summary?.optimized_top10 as FleetResultRow[] | undefined) ??
    [];
  const finalTop = filterBeatsBuyHold(finalTopRaw, bhNet);
  if (finalTop.length || buyHold) {
    const title = buyHold ? t("backtest.top10_beats_bh") : t("backtest.top10_final");
    const block = renderResultsTable(finalTop.slice(0, 10), title, props.stakeUsd, {
      deploy: callbacks.onCreateBotFromResult,
      buyHold,
      onOpenGlossaryStrategy: callbacks.onOpenGlossaryStrategy,
    });
    block.dataset.testid = "backtest-fleet-top10";
    root.appendChild(block);
  }

  const results = props.results;
  if (results?.rankings?.length) {
    const filters = document.createElement("div");
    filters.className = "gp-tab-row";
    filters.dataset.testid = "backtest-fleet-filters";
    for (const mode of ["all", "timeframe", "strategy"] as FleetFilterMode[]) {
      const btn = document.createElement("button");
      btn.type = "button";
      btn.className = props.filterMode === mode ? "gp-btn-primary" : "gp-btn-secondary";
      btn.textContent = t(`backtest.filter.${mode}`);
      btn.addEventListener("click", () => callbacks.onFilterChange(mode, props.filterTimeframe));
      filters.appendChild(btn);
    }
    root.appendChild(filters);
    const pass1Rows = filterBeatsBuyHold(results.rankings, bhNet);
    root.appendChild(
      renderResultsTable(pass1Rows, t("backtest.pass1_results"), props.stakeUsd, {
        buyHold,
        onOpenGlossaryStrategy: callbacks.onOpenGlossaryStrategy,
      }),
    );
  } else if (!props.loading && active?.status !== "running" && !finalTop.length && !buyHold) {
    const empty = document.createElement("p");
    empty.className = "gp-body";
    empty.textContent = t("backtest.empty");
    root.appendChild(empty);
  }

  return { root, cleanup: () => {} };
}
