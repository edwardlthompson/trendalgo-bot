export const TRADINGVIEW_INTERVALS = [
  "1S", "5S", "15S", "30S", "1", "3", "5", "15", "30", "45", "60", "120", "180", "240", "1D", "1W",
] as const;

export const TRADINGVIEW_INTERVAL_LABELS: Record<string, string> = {
  "1S": "1 second",
  "5S": "5 seconds",
  "15S": "15 seconds",
  "30S": "30 seconds",
  "1": "1 minute",
  "3": "3 minutes",
  "5": "5 minutes",
  "15": "15 minutes",
  "30": "30 minutes",
  "45": "45 minutes",
  "60": "1 hour",
  "120": "2 hours",
  "180": "3 hours",
  "240": "4 hours",
  "1D": "1 day",
  "1W": "1 week",
};

const LEGACY: Record<string, string> = { "1h": "60", "1d": "1D", "1w": "1W", "4h": "240" };

export function normalizeTimeframe(raw: string): string {
  if (TRADINGVIEW_INTERVALS.includes(raw as (typeof TRADINGVIEW_INTERVALS)[number])) return raw;
  return LEGACY[raw.toLowerCase()] ?? "60";
}

export function timeframeLabel(id: string): string {
  return TRADINGVIEW_INTERVAL_LABELS[id] ?? id;
}
