import type { ExchangeFeeSchedule } from "../api/client";

const BUNDLED_EXCHANGE_FEES: ExchangeFeeSchedule[] = [{"exchange_id": "binance", "taker_pct": 0.001, "maker_pct": 0.001, "tier": "retail_default", "source_url": "https://www.binance.com/en/fee/schedule"}, {"exchange_id": "binanceus", "taker_pct": 0.0001, "maker_pct": 0.0, "tier": "retail_default", "source_url": "https://www.binance.us/fees"}, {"exchange_id": "bitstamp", "taker_pct": 0.004, "maker_pct": 0.003, "tier": "retail_default", "source_url": "https://www.bitstamp.net/fee-schedule/"}, {"exchange_id": "bybit", "taker_pct": 0.001, "maker_pct": 0.001, "tier": "retail_default", "source_url": "https://www.bybit.com/en/help-center/article/Trading-Fee-Structure"}, {"exchange_id": "coinbaseadvanced", "taker_pct": 0.006, "maker_pct": 0.004, "tier": "retail_default", "source_url": "https://help.coinbase.com/en/coinbase/trading-and-funding/advanced-trade/advanced-trade-fees"}, {"exchange_id": "cryptocom", "taker_pct": 0.005, "maker_pct": 0.0025, "tier": "retail_default", "source_url": "https://crypto.com/exchange/document/fees-limits"}, {"exchange_id": "gemini", "taker_pct": 0.012, "maker_pct": 0.006, "tier": "retail_default", "source_url": "https://www.gemini.com/fees/activetrader-fee-schedule"}, {"exchange_id": "kraken", "taker_pct": 0.0026, "maker_pct": 0.0016, "tier": "retail_default", "source_url": "https://www.kraken.com/features/fee-schedule"}, {"exchange_id": "okx", "taker_pct": 0.0035, "maker_pct": 0.002, "tier": "retail_default", "source_url": "https://www.okx.com/fees"}];

export function bundledExchangeFees(): ExchangeFeeSchedule[] {
  return BUNDLED_EXCHANGE_FEES;
}

export function mergeFeeCatalogs(
  api: ExchangeFeeSchedule[],
  existing: ExchangeFeeSchedule[] = [],
): ExchangeFeeSchedule[] {
  const map = new Map(bundledExchangeFees().map((e) => [e.exchange_id, e]));
  for (const row of existing) map.set(row.exchange_id, row);
  for (const row of api) map.set(row.exchange_id, row);
  return [...map.values()].sort((a, b) => a.exchange_id.localeCompare(b.exchange_id));
}

export function feeForExchange(
  exchangeId: string,
  catalog: ExchangeFeeSchedule[],
): ExchangeFeeSchedule | null {
  return (
    catalog.find((e) => e.exchange_id === exchangeId) ??
    bundledExchangeFees().find((e) => e.exchange_id === exchangeId) ??
    null
  );
}
