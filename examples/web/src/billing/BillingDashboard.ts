import { t } from "../i18n";

export type BillingDashboardData = {
  enrollment: Record<string, unknown>;
  license_status: Record<string, unknown>;
  lifetime: {
    lifetime_gross_profit_usd: number;
    lifetime_license_fees_usd: number;
    lifetime_net_benefit_usd: number;
  };
  period_rollup: { gross_profit_usd: number; license_fee_usd: number; net_benefit_usd: number };
  current_period?: string;
  line_items: Array<Record<string, unknown>>;
  statements: Array<{ period: string; license_fee_usd: number }>;
  can_trade_live: boolean;
  dry_run_fee_preview: { rate_pct: number; sample_profit_usd: number; sample_fee_usd: number };
  disclaimer: string;
};

export type BillingCallbacks = {
  onEnroll: () => void;
  onProcessTrades: () => void;
  onOpenSettlement: () => void;
  onMarkPaid: () => void;
};

export function createBillingDashboard(
  data: BillingDashboardData,
  callbacks: BillingCallbacks,
): HTMLElement {
  const section = document.createElement("section");
  section.className = "gp-panel";
  section.dataset.testid = "billing-dashboard";
  section.innerHTML = `
    <h2 class="gp-panel-title">${t("billing.title")}</h2>
    <p class="gp-disclaimer">${data.disclaimer}</p>
    <p data-testid="lifetime-net">${t("billing.lifetime_net")}: $${data.lifetime.lifetime_net_benefit_usd.toFixed(2)}</p>
    <p>${t("billing.lifetime_fees")}: $${data.lifetime.lifetime_license_fees_usd.toFixed(2)}</p>
    <p data-testid="period-fee">${t("billing.period_fee")}: $${data.period_rollup.license_fee_usd.toFixed(2)}</p>
    <p class="gp-net-loss-note">${t("billing.net_loss_zero")}</p>
  `;

  const actions = document.createElement("div");
  actions.className = "gp-panel-actions";
  if (!data.enrollment.enrolled) {
    const enroll = document.createElement("button");
    enroll.type = "button";
    enroll.className = "gp-btn-primary";
    enroll.dataset.testid = "billing-enroll";
    enroll.textContent = t("billing.enroll");
    enroll.addEventListener("click", () => callbacks.onEnroll());
    actions.appendChild(enroll);
  }
  const process = document.createElement("button");
  process.type = "button";
  process.className = "gp-btn-secondary";
  process.dataset.testid = "billing-process";
  process.textContent = t("billing.process");
  process.addEventListener("click", () => callbacks.onProcessTrades());
  const settle = document.createElement("button");
  settle.type = "button";
  settle.className = "gp-btn-secondary";
  settle.dataset.testid = "billing-settle";
  settle.textContent = t("billing.settle");
  settle.addEventListener("click", () => callbacks.onOpenSettlement());
  const paid = document.createElement("button");
  paid.type = "button";
  paid.className = "gp-btn-secondary";
  paid.dataset.testid = "billing-mark-paid";
  paid.textContent = t("billing.mark_paid");
  paid.addEventListener("click", () => callbacks.onMarkPaid());
  actions.append(process, settle, paid);
  section.appendChild(actions);

  const preview = document.createElement("p");
  preview.className = "gp-body";
  preview.textContent = `${t("billing.preview")}: ${(data.dry_run_fee_preview.rate_pct * 100).toFixed(0)}% on $${data.dry_run_fee_preview.sample_profit_usd} = $${data.dry_run_fee_preview.sample_fee_usd}`;
  section.appendChild(preview);

  const table = document.createElement("table");
  table.className = "gp-holdings-table";
  table.innerHTML = `<thead><tr><th>Pair</th><th>P/L</th><th>Fee</th><th>Rule</th></tr></thead><tbody></tbody>`;
  const tbody = table.querySelector("tbody")!;
  for (const row of data.line_items.slice(0, 20)) {
    const tr = document.createElement("tr");
    tr.innerHTML = `<td>${row.pair}</td><td>$${Number(row.gross_profit_usd).toFixed(2)}</td><td>$${Number(row.license_fee_usd).toFixed(2)}</td><td>${row.rule_applied}</td>`;
    tbody.appendChild(tr);
  }
  section.appendChild(table);
  return section;
}
