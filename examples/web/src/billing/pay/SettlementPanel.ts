import { t } from "../../i18n";
import {
  amountDecimals,
  renderSettlementStatus,
  sendAmount,
  SETTLEMENT_POLL_MS,
} from "./settlementPanelHelpers";
import type { SettlementCallbacks, SettlementData } from "./settlementPanelTypes";

export type { SettlementAssetOption, SettlementCallbacks, SettlementData } from "./settlementPanelTypes";

export function createSettlementPanel(
  data: SettlementData,
  callbacks: SettlementCallbacks,
): HTMLElement {
  const section = document.createElement("section");
  section.className = "gp-panel";
  section.dataset.testid = "billing-settlement";

  const statusEl = document.createElement("p");
  statusEl.dataset.testid = "settlement-status";

  const applyStatus = (payload: SettlementData) => {
    const status = renderSettlementStatus(payload);
    statusEl.textContent = status.text;
    statusEl.className = status.className;
  };

  applyStatus(data);

  const toSend = sendAmount(data);
  const chainLabel = data.chain ? data.chain.charAt(0).toUpperCase() + data.chain.slice(1) : "";

  section.innerHTML = `
    <h3>${t("billing.settlement_title")}</h3>
    <p class="gp-disclaimer">${data.disclaimer}</p>
    <p>${t("billing.settlement_amount")}: $${data.amount_usd.toFixed(2)} (${data.period})</p>
    <p data-testid="settlement-amount">${toSend != null ? `${t("billing.send_exact")}: ${toSend.toFixed(amountDecimals(data.asset))} ${data.asset}${chainLabel ? ` · ${chainLabel}` : ""}` : ""}</p>
    <p data-testid="settlement-reference">${data.payment_reference ? `${t("billing.payment_ref")}: ${data.payment_reference}` : ""}</p>
    <p data-testid="settlement-address">${t("billing.pay_to")}: ${data.address}</p>
    <p class="gp-body">${data.payment_instructions ?? ""}</p>
    <pre class="gp-research-output" data-testid="settlement-qr">${data.qr_payload}</pre>
  `;
  section.insertBefore(statusEl, section.querySelector(".gp-disclaimer"));

  if (callbacks.assets && callbacks.assets.length > 1) {
    const assetRow = document.createElement("div");
    assetRow.className = "gp-panel-actions";
    const label = document.createElement("label");
    label.className = "gp-body";
    label.textContent = `${t("billing.pay_with")}: `;
    const select = document.createElement("select");
    select.dataset.testid = "settlement-asset";
    select.className = "gp-select";
    for (const opt of callbacks.assets) {
      const option = document.createElement("option");
      option.value = opt.asset;
      option.textContent = `${opt.label} (${opt.chain})`;
      option.selected = opt.asset === (callbacks.selectedAsset ?? data.asset);
      select.appendChild(option);
    }
    select.addEventListener("change", () => callbacks.onAssetChange?.(select.value));
    label.appendChild(select);
    assetRow.appendChild(label);
    section.insertBefore(assetRow, section.querySelector(".gp-disclaimer"));
  }

  const actions = document.createElement("div");
  actions.className = "gp-panel-actions";
  const copy = document.createElement("button");
  copy.type = "button";
  copy.className = "gp-btn-primary";
  copy.dataset.testid = "copy-address";
  copy.textContent = t("billing.copy_address");
  copy.addEventListener("click", () => callbacks.onCopy(data.address));
  const copyAmt = document.createElement("button");
  copyAmt.type = "button";
  copyAmt.className = "gp-btn-secondary";
  copyAmt.dataset.testid = "copy-amount";
  copyAmt.textContent = t("billing.copy_amount");
  copyAmt.addEventListener("click", () => {
    const amt = sendAmount(data);
    if (amt != null) callbacks.onCopy(String(amt));
  });
  const ln = document.createElement("button");
  ln.type = "button";
  ln.className = "gp-btn-secondary";
  ln.textContent = t("billing.lightning");
  ln.addEventListener("click", () => callbacks.onLightning());
  actions.append(copy, copyAmt, ln);
  section.appendChild(actions);

  let pollTimer: number | undefined;
  if (
    data.payment_id &&
    data.status === "pending" &&
    data.auto_verify !== false &&
    callbacks.onPoll
  ) {
    const paymentId = data.payment_id;
    const tick = () => {
      void callbacks.onPoll?.(paymentId).then((next) => {
        if (!next) return;
        applyStatus(next);
        if (next.status === "confirmed") {
          if (pollTimer != null) window.clearInterval(pollTimer);
          callbacks.onConfirmed?.(next);
        }
      });
    };
    tick();
    pollTimer = window.setInterval(tick, SETTLEMENT_POLL_MS);
  }

  const observer = new MutationObserver(() => {
    if (!document.contains(section) && pollTimer != null) {
      window.clearInterval(pollTimer);
      pollTimer = undefined;
    }
  });
  observer.observe(document.body, { childList: true, subtree: true });

  return section;
}
