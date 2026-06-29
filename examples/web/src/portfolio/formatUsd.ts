import {
  convertFromUsd,
  getDisplayCurrency,
  type DisplayCurrencyCode,
} from "../settings/displayCurrency";

export function formatUsd(value: number, options?: { signed?: boolean }): string {
  const currency = getDisplayCurrency();
  const amount = convertFromUsd(value, currency);
  const fractionDigits = currency === "JPY" ? 0 : 2;
  return new Intl.NumberFormat(undefined, {
    style: "currency",
    currency,
    minimumFractionDigits: fractionDigits,
    maximumFractionDigits: fractionDigits,
    signDisplay: options?.signed ? "always" : "auto",
  }).format(amount);
}

export function formatPct(value: number, options?: { signed?: boolean }): string {
  const pct = value * 100;
  const sign = options?.signed && pct >= 0 ? "+" : "";
  return `${sign}${pct.toFixed(2)}%`;
}

export { getDisplayCurrency, type DisplayCurrencyCode };
