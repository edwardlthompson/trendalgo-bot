import { describe, expect, it } from "vitest";
import { buildExchangeSegments, sortAccountsByValue } from "./exchangeSegments";
import type { ExchangeIconMeta } from "./iconRegistry";

const registry = new Map<string, ExchangeIconMeta>([
  ["kraken", { brand: "Kraken", color: "#5741D9", icon: "/icons/exchanges/kraken.svg" }],
  ["binance", { brand: "Binance", color: "#F3BA2F", icon: "/icons/exchanges/binance.svg" }],
]);

describe("exchangeSegments", () => {
  it("sorts accounts by USD descending", () => {
    const sorted = sortAccountsByValue([
      { account_id: 1, exchange: "a", label: "d", account_type: "spot", total_usd: 100, holdings_count: 1 },
      { account_id: 2, exchange: "b", label: "d", account_type: "spot", total_usd: 500, holdings_count: 2 },
    ]);
    expect(sorted[0].total_usd).toBe(500);
  });

  it("builds segment widths that sum to ~100%", () => {
    const segments = buildExchangeSegments(
      [
        { account_id: 1, exchange: "kraken", label: "d", account_type: "spot", total_usd: 750, holdings_count: 3 },
        { account_id: 2, exchange: "binance", label: "d", account_type: "spot", total_usd: 250, holdings_count: 2 },
      ],
      1000,
      registry,
    );
    expect(segments[0].exchange).toBe("kraken");
    expect(segments[0].widthPct).toBeCloseTo(75, 1);
    expect(segments[1].widthPct).toBeCloseTo(25, 1);
    expect(segments[0].color).toBe("#5741D9");
  });
});
