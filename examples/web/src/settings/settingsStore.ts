import type { TaLibraryCategory } from "../api/client";
import { buildFallbackTaLibrary } from "../data/taLibraryFallback";

const PREFIX = "trendalgo.settings.v1";

export type PersistedBotSettings = {
  label: string;
  strategy_id: string;
  pair: string;
  exchange: string;
  timeframe: string;
  equity_mode: "base" | "quote" | "portfolio_pct";
  equity_input: number;
  ta_params: Record<string, number>;
};

type SettingsRoot = {
  bots: Record<string, PersistedBotSettings>;
  taLibrary: TaLibraryCategory[] | null;
  pairsByExchange: Record<string, string[]>;
};

function readRoot(): SettingsRoot {
  try {
    const raw = localStorage.getItem(PREFIX);
    if (!raw) return { bots: {}, taLibrary: null, pairsByExchange: {} };
    const parsed = JSON.parse(raw) as SettingsRoot;
    return {
      bots: parsed.bots ?? {},
      taLibrary: parsed.taLibrary ?? null,
      pairsByExchange: parsed.pairsByExchange ?? {},
    };
  } catch {
    return { bots: {}, taLibrary: null, pairsByExchange: {} };
  }
}

function writeRoot(root: SettingsRoot): void {
  localStorage.setItem(PREFIX, JSON.stringify(root));
}

export function loadBotSettings(botId: number): PersistedBotSettings | null {
  return readRoot().bots[String(botId)] ?? null;
}

export function saveBotSettings(botId: number, settings: PersistedBotSettings): void {
  const root = readRoot();
  root.bots[String(botId)] = settings;
  writeRoot(root);
}

export function loadCachedTaLibrary(): TaLibraryCategory[] {
  const cached = readRoot().taLibrary;
  if (cached?.length) return cached;
  return buildFallbackTaLibrary();
}

export function saveCachedTaLibrary(categories: TaLibraryCategory[]): void {
  const root = readRoot();
  root.taLibrary = categories;
  writeRoot(root);
}

export function loadCachedPairs(exchangeId: string): string[] | null {
  const pairs = readRoot().pairsByExchange[exchangeId];
  return pairs?.length ? pairs : null;
}

export function saveCachedPairs(exchangeId: string, pairs: string[]): void {
  const root = readRoot();
  root.pairsByExchange[exchangeId] = pairs;
  writeRoot(root);
}

export function mergeBotWithPersisted<T extends Record<string, unknown>>(
  botId: number,
  bot: T,
): T & Partial<PersistedBotSettings> {
  const saved = loadBotSettings(botId);
  if (!saved) return bot;
  return { ...bot, ...saved };
}
