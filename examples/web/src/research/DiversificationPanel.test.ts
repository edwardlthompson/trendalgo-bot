import { describe, expect, it } from "vitest";
import { correlationCellColor, createDiversificationPanel } from "./DiversificationPanel";

describe("DiversificationPanel", () => {
  it("correlationCellColor spans red to green", () => {
    expect(correlationCellColor(-1)).toMatch(/^hsl\(0 /);
    expect(correlationCellColor(1)).toMatch(/^hsl\(142 /);
  });

  it("renders row and column headers in correlation matrix", () => {
    const el = createDiversificationPanel(["Tip one"], {
      assets: ["BTC", "ETH"],
      matrix: [
        [1, 0.35],
        [0.35, 1],
      ],
    });
    const table = el.querySelector('[data-testid="correlation-matrix"]')!;
    expect(table.querySelectorAll("thead th")).toHaveLength(3);
    expect(table.querySelectorAll("tbody th.gp-corr-row-head")).toHaveLength(2);
    expect(table.querySelectorAll(".gp-corr-cell")).toHaveLength(4);
  });
});
