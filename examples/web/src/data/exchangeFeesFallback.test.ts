import { describe, expect, it } from "vitest";
import {
  bundledExchangeFees,
  feeForExchange,
  mergeFeeCatalogs,
} from "./exchangeFeesFallback";

describe("exchangeFeesFallback", () => {
  it("includes kraken and binanceus retail fees", () => {
    const kraken = feeForExchange("kraken", bundledExchangeFees());
    const binanceus = feeForExchange("binanceus", bundledExchangeFees());
    expect(kraken?.taker_pct).toBe(0.0026);
    expect(binanceus?.taker_pct).toBe(0.0001);
  });

  it("prefers API rows when merging catalogs", () => {
    const merged = mergeFeeCatalogs([
      {
        exchange_id: "kraken",
        taker_pct: 0.003,
        maker_pct: 0.002,
        tier: "retail_default",
        source_url: "https://api",
      },
    ]);
    expect(feeForExchange("kraken", merged)?.taker_pct).toBe(0.003);
    expect(feeForExchange("binanceus", merged)?.taker_pct).toBe(0.0001);
  });
});
