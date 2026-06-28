import { describe, expect, it } from "vitest";
import { DUST_THRESHOLD_USD, filterHoldings, sortHoldings } from "./holdingsSort";

describe("sortHoldings", () => {
  const holdings = [
    { asset: "ETH", value_usd: 2000, unrealized_pnl_usd: 100 },
    { asset: "BTC", value_usd: 50000, unrealized_pnl_usd: -500 },
    { asset: "SOL", value_usd: 800, unrealized_pnl_usd: 1200 },
  ];

  it("sorts by value descending by default", () => {
    const sorted = sortHoldings(holdings, "value");
    expect(sorted.map((h) => h.asset)).toEqual(["BTC", "ETH", "SOL"]);
  });

  it("sorts by unrealized descending", () => {
    const sorted = sortHoldings(holdings, "unrealized");
    expect(sorted.map((h) => h.asset)).toEqual(["SOL", "ETH", "BTC"]);
  });

  it("sorts ascending when requested", () => {
    const sorted = sortHoldings(holdings, "value", "asc");
    expect(sorted.map((h) => h.asset)).toEqual(["SOL", "ETH", "BTC"]);
  });
});

describe("filterHoldings", () => {
  it("returns all holdings when hideDust is false", () => {
    const holdings = [
      { asset: "BTC", value_usd: 100 },
      { asset: "DUST", value_usd: 2 },
    ];
    expect(filterHoldings(holdings, { hideDust: false })).toHaveLength(2);
  });

  it("hides holdings below dust threshold", () => {
    const holdings = [
      { asset: "BTC", value_usd: 100 },
      { asset: "EDGE", value_usd: DUST_THRESHOLD_USD },
      { asset: "DUST", value_usd: 9.99 },
    ];
    const filtered = filterHoldings(holdings, { hideDust: true });
    expect(filtered.map((h) => h.asset)).toEqual(["BTC", "EDGE"]);
  });
});
