export function formatUsd(value: number, options?: { signed?: boolean }): string {
  return new Intl.NumberFormat(undefined, {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
    signDisplay: options?.signed ? "always" : "auto",
  }).format(value);
}

export function formatPct(value: number, options?: { signed?: boolean }): string {
  const pct = value * 100;
  const sign = options?.signed && pct >= 0 ? "+" : "";
  return `${sign}${pct.toFixed(2)}%`;
}
