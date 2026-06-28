import { describe, expect, it } from "vitest";
import { heatmapColor, heatmapFromHoldings } from "./Heatmap";

describe("heatmapColor", () => {
  it("returns green for gains, yellow near zero, and red for losses", () => {
    expect(heatmapColor(20)).toMatch(/^hsl\(142/);
    expect(heatmapColor(0)).toMatch(/^hsl\(48/);
    expect(heatmapColor(-20)).toMatch(/^hsl\(0 /);
    expect(heatmapColor(10)).toMatch(/^hsl\((9[0-9]|1[0-3][0-9]|14[0-2]) /);
  });
});

describe("heatmapFromHoldings", () => {
  it("builds rows only from held assets", () => {
    const rows = heatmapFromHoldings([
      { asset: "BTC", pct_change: 0.05 },
      { asset: "ETH", pct_change: -0.02 },
    ]);
    expect(rows.map((r) => r.asset)).toEqual(["BTC", "ETH"]);
    expect(rows[0].return_pct).toBe(5);
  });
});
