import { describe, expect, it } from "vitest";
import { glossaryCategoriesWithCounts, setTaGlossaryEntries } from "./taGlossary";

describe("glossaryCategoriesWithCounts", () => {
  it("groups entries by category in display order", () => {
    setTaGlossaryEntries([
      {
        id: "RSI",
        title: "RSI",
        category: "Momentum Indicators",
        short: "s",
        long: "l",
        formula: "f",
      },
      {
        id: "MACD",
        title: "MACD",
        category: "Momentum Indicators",
        short: "s",
        long: "l",
        formula: "f",
      },
      {
        id: "SMA",
        title: "SMA",
        category: "Overlap Studies",
        short: "s",
        long: "l",
        formula: "f",
      },
    ]);
    const rows = glossaryCategoriesWithCounts();
    expect(rows).toEqual([
      { category: "Overlap Studies", count: 1 },
      { category: "Momentum Indicators", count: 2 },
    ]);
  });
});
