import exchangesRegistry from "../../public/icon-registry/exchanges.json";
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

const FALLBACK_EXCHANGES: Record<string, ExchangeIconMeta> = Object.fromEntries(
  Object.entries(exchangesRegistry.exchanges).map(([id, meta]) => [
    id,
    { brand: meta.brand, color: meta.color, icon: meta.icon },
  ]),
);

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
      color: "var(--gp-color-outline)",
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
