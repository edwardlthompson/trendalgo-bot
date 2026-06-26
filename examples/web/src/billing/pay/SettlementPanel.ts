import { t } from "../../i18n";

export type SettlementData = {
  period: string;
  amount_usd: number;
  address: string;
  asset: string;
  qr_payload: string;
  disclaimer: string;
  user_initiated_only: boolean;
};

export function createSettlementPanel(
  data: SettlementData,
  onCopy: (text: string) => void,
  onLightning: () => void,
): HTMLElement {
  const section = document.createElement("section");
  section.className = "gp-panel";
  section.dataset.testid = "billing-settlement";
  section.innerHTML = `
    <h3>${t("billing.settlement_title")}</h3>
    <p class="gp-disclaimer">${data.disclaimer}</p>
    <p>${t("billing.settlement_amount")}: $${data.amount_usd.toFixed(2)} (${data.period})</p>
    <p data-testid="settlement-address">${data.asset}: ${data.address}</p>
    <pre class="gp-research-output" data-testid="settlement-qr">${data.qr_payload}</pre>
  `;
  const copy = document.createElement("button");
  copy.type = "button";
  copy.className = "gp-btn-primary";
  copy.dataset.testid = "copy-address";
  copy.textContent = t("billing.copy_address");
  copy.addEventListener("click", () => onCopy(data.address));
  const ln = document.createElement("button");
  ln.type = "button";
  ln.className = "gp-btn-secondary";
  ln.textContent = t("billing.lightning");
  ln.addEventListener("click", onLightning);
  section.append(copy, ln);
  return section;
}
