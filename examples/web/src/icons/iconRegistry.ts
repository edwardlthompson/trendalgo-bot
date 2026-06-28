import { resolveCoinSymbol } from "./coinAliases";

export type ExchangeIconMeta = {
  brand: string;
  color: string;
  icon: string;
};

export type CoinIconMeta = {
  name: string;
  coingecko_id: string;
  icon: string;
  rank?: number;
};

type ExchangeRegistryFile = {
  version: number;
  exchanges: Record<string, ExchangeIconMeta>;
};

type CoinRegistryFile = {
  version: number;
  count: number;
  coins: Record<string, CoinIconMeta>;
};

let exchangeCache: Map<string, ExchangeIconMeta> | null = null;
let coinCache: Map<string, CoinIconMeta> | null = null;
let coinLoadPromise: Promise<Map<string, CoinIconMeta>> | null = null;

const FALLBACK_EXCHANGES: Record<string, ExchangeIconMeta> = {
  kraken: { brand: "Kraken", color: "#5741D9", icon: "/icons/exchanges/kraken.jpg" },
  binanceus: { brand: "Binance.US", color: "#F0B90B", icon: "/icons/exchanges/binanceus.png" },
  coinbaseadvanced: { brand: "Coinbase Advanced", color: "#0052FF", icon: "/icons/exchanges/coinbaseadvanced.png" },
  gemini: { brand: "Gemini", color: "#00DCFA", icon: "/icons/exchanges/gemini.png" },
  bitstamp: { brand: "Bitstamp", color: "#1C3584", icon: "/icons/exchanges/bitstamp.jpg" },
  cryptocom: { brand: "Crypto.com", color: "#1199FA", icon: "/icons/exchanges/cryptocom.jpg" },
  binance: { brand: "Binance", color: "#F3BA2F", icon: "/icons/exchanges/binance.jpg" },
  bybit: { brand: "Bybit", color: "#F7A600", icon: "/icons/exchanges/bybit.png" },
  okx: { brand: "OKX", color: "#2B2B2B", icon: "/icons/exchanges/okx.png" },
};

export async function loadExchangeIcons(): Promise<Map<string, ExchangeIconMeta>> {
  if (exchangeCache) return exchangeCache;
  try {
    const res = await fetch("/icon-registry/exchanges.json");
    if (res.ok) {
      const data = (await res.json()) as ExchangeRegistryFile;
      exchangeCache = new Map(Object.entries(data.exchanges));
      return exchangeCache;
    }
  } catch {
    /* use fallback */
  }
  exchangeCache = new Map(Object.entries(FALLBACK_EXCHANGES));
  return exchangeCache;
}

export async function loadCoinIcons(): Promise<Map<string, CoinIconMeta>> {
  if (coinCache) return coinCache;
  if (!coinLoadPromise) {
    coinLoadPromise = (async () => {
      try {
        const res = await fetch("/icon-registry/coins.json");
        if (res.ok) {
          const data = (await res.json()) as CoinRegistryFile;
          coinCache = new Map(
            Object.entries(data.coins).map(([symbol, meta]) => [symbol.toUpperCase(), meta]),
          );
          for (const [symbol, meta] of Object.entries(data.coins)) {
            const canonical = resolveCoinSymbol(symbol);
            if (!coinCache.has(canonical)) {
              coinCache.set(canonical, { ...meta, icon: meta.icon });
            }
          }
          return coinCache;
        }
      } catch {
        /* empty registry */
      }
      coinCache = new Map();
      return coinCache;
    })();
  }
  return coinLoadPromise;
}

export function exchangeMeta(
  registry: Map<string, ExchangeIconMeta>,
  exchangeId: string,
): ExchangeIconMeta {
  return (
    registry.get(exchangeId) ?? {
      brand: exchangeId,
      color: "#888888",
      icon: "/icons/exchanges/generic.png",
    }
  );
}

export function coinIconUrl(registry: Map<string, CoinIconMeta>, symbol: string): string {
  const canonical = resolveCoinSymbol(symbol);
  return (
    registry.get(canonical)?.icon ??
    registry.get(symbol.toUpperCase())?.icon ??
    "/icons/coins/generic.svg"
  );
}
