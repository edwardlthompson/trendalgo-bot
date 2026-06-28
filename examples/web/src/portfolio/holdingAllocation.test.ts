import { describe, expect, it } from "vitest";
import { holdingAllocationPct } from "./holdingAllocation";

describe("holdingAllocationPct", () => {
  it("computes weight from value over portfolio total", () => {
    expect(holdingAllocationPct(25_000, 100_000)).toBeCloseTo(0.25);
    expect(holdingAllocationPct(0, 100_000)).toBe(0);
    expect(holdingAllocationPct(100, 0)).toBe(0);
  });
});
