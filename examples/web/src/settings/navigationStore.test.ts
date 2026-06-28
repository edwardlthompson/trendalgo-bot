import { beforeEach, describe, expect, it } from "vitest";
import { loadNavigation, saveNavigation } from "./navigationStore";

const KEY = "trendalgo.navigation.v1";

describe("navigationStore", () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it("defaults to portfolio when nothing saved", () => {
    expect(loadNavigation()).toEqual({ view: "portfolio", selectedBotId: null });
  });

  it("round-trips view and bot detail", () => {
    saveNavigation({ view: "backtest", selectedBotId: null });
    expect(loadNavigation()).toEqual({ view: "backtest", selectedBotId: null });

    saveNavigation({ view: "dashboard", selectedBotId: 42 });
    expect(loadNavigation()).toEqual({ view: "dashboard", selectedBotId: 42 });
  });

  it("clears bot id when view is not dashboard", () => {
    saveNavigation({ view: "scanner", selectedBotId: 7 });
    expect(loadNavigation()).toEqual({ view: "scanner", selectedBotId: null });
  });

  it("rejects invalid view", () => {
    localStorage.setItem(KEY, JSON.stringify({ view: "unknown", selectedBotId: 1 }));
    expect(loadNavigation()).toEqual({ view: "portfolio", selectedBotId: null });
  });

  it("maps legacy strategies view to dashboard", () => {
    localStorage.setItem(KEY, JSON.stringify({ view: "strategies", selectedBotId: null }));
    expect(loadNavigation()).toEqual({ view: "dashboard", selectedBotId: null });
  });
});
