import { t } from "../../i18n";
import type { SettlementData } from "./settlementPanelTypes";

export const SETTLEMENT_POLL_MS = 12_000;

export function formatLicensedUntil(iso: string | undefined): string {
  if (!iso) return "";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleDateString(undefined, { year: "numeric", month: "long", day: "numeric" });
}

export function sendAmount(data: SettlementData): number | null {
  if (data.amount_to_send != null) return data.amount_to_send;
  if (data.amount_btc != null && data.asset === "BTC") return data.amount_btc;
  return null;
}

export function amountDecimals(asset: string): number {
  return asset === "BTC" ? 8 : 6;
}

export function renderSettlementStatus(payload: SettlementData): { text: string; className: string } {
  if (payload.status === "confirmed") {
    return {
      text: t("billing.payment_confirmed", { until: formatLicensedUntil(payload.licensed_until) }),
      className: "gp-body gp-text-success",
    };
  }
  if (payload.status === "expired") {
    return { text: t("billing.payment_expired"), className: "gp-body gp-text-error" };
  }
  return { text: t("billing.payment_watching"), className: "gp-body" };
}
