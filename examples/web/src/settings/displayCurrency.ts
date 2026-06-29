/** Display fiat preference — USD-denominated values converted for UI. */

export const DISPLAY_CURRENCIES = [
  { code: "USD", label: "US Dollar (USD)" },
  { code: "EUR", label: "Euro (EUR)" },
  { code: "GBP", label: "British Pound (GBP)" },
  { code: "JPY", label: "Japanese Yen (JPY)" },
  { code: "CAD", label: "Canadian Dollar (CAD)" },
  { code: "AUD", label: "Australian Dollar (AUD)" },
  { code: "CHF", label: "Swiss Franc (CHF)" },
] as const;

export type DisplayCurrencyCode = (typeof DISPLAY_CURRENCIES)[number]["code"];

const STORAGE_KEY = "gp-display-currency";
const RATES_KEY = "gp-fx-rates-usd";
const RATES_TS_KEY = "gp-fx-rates-ts";
const RATES_TTL_MS = 24 * 60 * 60 * 1000;

const FALLBACK_USD_RATES: Record<DisplayCurrencyCode, number> = {
  USD: 1,
  EUR: 0.92,
  GBP: 0.79,
  JPY: 150,
  CAD: 1.36,
  AUD: 1.52,
  CHF: 0.88,
};

let cachedRates: Record<string, number> = { ...FALLBACK_USD_RATES };
const listeners = new Set<() => void>();

function notify(): void {
  listeners.forEach((fn) => fn());
}

export function subscribeDisplayCurrencyChange(listener: () => void): () => void {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

export function isDisplayCurrencyCode(value: string): value is DisplayCurrencyCode {
  return DISPLAY_CURRENCIES.some((row) => row.code === value);
}

export function getDisplayCurrency(): DisplayCurrencyCode {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (raw && isDisplayCurrencyCode(raw)) return raw;
  } catch {
    /* ignore */
  }
  return "USD";
}

export function setDisplayCurrency(code: DisplayCurrencyCode): void {
  localStorage.setItem(STORAGE_KEY, code);
  notify();
}

function loadCachedRates(): Record<string, number> {
  try {
    const ts = Number(localStorage.getItem(RATES_TS_KEY) || "0");
    const raw = localStorage.getItem(RATES_KEY);
    if (raw && Date.now() - ts < RATES_TTL_MS) {
      const parsed = JSON.parse(raw) as Record<string, number>;
      return { USD: 1, ...parsed };
    }
  } catch {
    /* ignore */
  }
  return { ...FALLBACK_USD_RATES };
}

function saveCachedRates(rates: Record<string, number>): void {
  const { USD: _usd, ...rest } = rates;
  localStorage.setItem(RATES_KEY, JSON.stringify(rest));
  localStorage.setItem(RATES_TS_KEY, String(Date.now()));
}

export function getUsdFxRates(): Record<string, number> {
  return cachedRates;
}

export async function refreshUsdFxRates(): Promise<void> {
  cachedRates = loadCachedRates();
  const codes = DISPLAY_CURRENCIES.map((c) => c.code).filter((c) => c !== "USD");
  try {
    const res = await fetch(
      `https://api.frankfurter.app/latest?from=USD&to=${codes.join(",")}`,
    );
    if (!res.ok) return;
    const body = (await res.json()) as { rates?: Record<string, number> };
    if (body.rates) {
      cachedRates = { USD: 1, ...body.rates };
      saveCachedRates(cachedRates);
    }
  } catch {
    /* offline — keep cached or fallback */
  }
}

export function initDisplayCurrency(): void {
  cachedRates = loadCachedRates();
  void refreshUsdFxRates();
}

export function convertFromUsd(amountUsd: number, code: DisplayCurrencyCode = getDisplayCurrency()): number {
  const rate = cachedRates[code] ?? FALLBACK_USD_RATES[code] ?? 1;
  return amountUsd * rate;
}
