import { describe, expect, it } from "vitest";
import {
  beatsBuyHold,
  buyHoldNet,
  filterBeatsBuyHold,
  hasPositivePl,
  formatNetProfitPct,
  formatVsBuyHoldPct,
  strategyOptimizedMarker,
  vsBuyHoldAmount,
} from "./fleetResults";
import type { FleetResultRow } from "../api/client";

const row = (net: number, sid = "RSI"): FleetResultRow => ({
  strategy_id: sid,
  timeframe: "60",
  net_profit: net,
  gross_profit: net,
  fees_paid: 0,
  trades: 3,
  bar_count: 720,
});

describe("fleetResults", () => {
  it("filters rows strictly above buy-and-hold net", () => {
    const filtered = filterBeatsBuyHold([row(50), row(49.99), row(51)], 50);
    expect(filtered).toHaveLength(1);
    expect(filtered[0]?.net_profit).toBe(51);
  });

  it("excludes non-positive P&L even when above buy-and-hold", () => {
    const filtered = filterBeatsBuyHold([row(-1), row(0), row(5)], -10);
    expect(filtered).toHaveLength(1);
    expect(filtered[0]?.net_profit).toBe(5);
  });

  it("returns only positive rows when baseline is missing", () => {
    expect(filterBeatsBuyHold([row(-1), row(0), row(2)], null)).toEqual([row(2)]);
  });

  it("computes vs buy-and-hold delta", () => {
    expect(vsBuyHoldAmount(12.5, -10)).toBeCloseTo(22.5);
  });

  it("reads buy-and-hold net from summary", () => {
    expect(
      buyHoldNet({
        buy_and_hold: { net_profit: -198.65, strategy_id: "BUY_AND_HOLD", timeframe: "ALL" },
      }),
    ).toBe(-198.65);
  });

  it("beatsBuyHold requires strict greater-than", () => {
    expect(beatsBuyHold(row(50), 50)).toBe(false);
    expect(beatsBuyHold(row(50.01), 50)).toBe(true);
  });

  it("hasPositivePl requires net above zero", () => {
    expect(hasPositivePl(row(0.01))).toBe(true);
    expect(hasPositivePl(row(0))).toBe(false);
    expect(hasPositivePl(row(-1))).toBe(false);
  });

  it("formats net profit and vs B&H percent", () => {
    expect(formatNetProfitPct(12.5, 1000)).toBe("+1.25%");
    expect(formatVsBuyHoldPct(12.5, -10, 1000)).toBe("+2.25%");
  });

  it("detects optimized marker from fleet flags", () => {
    expect(strategyOptimizedMarker({ ...row(1), optimized: true })).toBe(true);
    expect(strategyOptimizedMarker(row(1))).toBe(false);
  });
});
