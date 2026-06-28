// @vitest-environment jsdom
import { describe, expect, it, beforeEach } from "vitest";
import { buildFallbackTaLibrary, TA_FUNCTION_NAMES } from "../data/taLibraryFallback";
import { KRAKEN_USD_PAIRS } from "../data/krakenUsdPairs";
import { loadCachedTaLibrary, saveBotSettings, loadBotSettings } from "./settingsStore";

describe("settingsStore", () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it("persists bot settings by id", () => {
    saveBotSettings(1, {
      label: "Bot-A",
      strategy_id: "RSI",
      pair: "ETH/USD",
      exchange: "kraken",
      timeframe: "60",
      equity_mode: "quote",
      equity_input: 500,
      ta_params: { timeperiod: 14 },
    });
    expect(loadBotSettings(1)?.pair).toBe("ETH/USD");
  });

  it("loads cached ta library fallback", () => {
    expect(loadCachedTaLibrary().flatMap((c) => c.items).length).toBeGreaterThan(100);
  });
});

describe("catalog fallbacks", () => {
  it("includes full TA library", () => {
    expect(TA_FUNCTION_NAMES.length).toBeGreaterThan(100);
    expect(buildFallbackTaLibrary().flatMap((c) => c.items).length).toBeGreaterThan(100);
  });

  it("includes 100+ kraken pairs", () => {
    expect(KRAKEN_USD_PAIRS.length).toBeGreaterThan(100);
  });
});
