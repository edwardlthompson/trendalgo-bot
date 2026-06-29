import { beforeEach, describe, expect, it } from "vitest";
import {
  convertFromUsd,
  getDisplayCurrency,
  setDisplayCurrency,
} from "./displayCurrency";

describe("displayCurrency", () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it("defaults to USD", () => {
    expect(getDisplayCurrency()).toBe("USD");
  });

  it("persists selection", () => {
    setDisplayCurrency("EUR");
    expect(getDisplayCurrency()).toBe("EUR");
  });

  it("converts from USD using fallback rates", () => {
    setDisplayCurrency("EUR");
    expect(convertFromUsd(100, "EUR")).toBeCloseTo(92, 0);
  });
});
