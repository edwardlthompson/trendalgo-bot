/** Exchange ticker aliases → canonical symbols in coins.json */
export const COIN_ALIASES: Record<string, string> = {
  XBT: "BTC",
  XXBT: "BTC",
  BIT: "BTC",
  TBTC: "BTC",
  WBTC: "BTC",
  XETH: "ETH",
  XXDG: "DOGE",
  XDG: "DOGE",
  XLTC: "LTC",
  XXRP: "XRP",
  XXLM: "XLM",
  XZEC: "ZEC",
  XXMR: "XMR",
  REPV2: "REP",
  MSOL: "SOL",
  POL: "MATIC",
  WAXL: "AXL",
};

export function resolveCoinSymbol(symbol: string): string {
  const upper = symbol.trim().toUpperCase();
  return COIN_ALIASES[upper] ?? upper;
}
