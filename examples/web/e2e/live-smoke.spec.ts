/**
 * Live smoke against running dev stack (API :8000 + Vite :5173).
 * Run: npx playwright test e2e/live-smoke.spec.ts --config=playwright.live.config.ts
 */
import { test, expect } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";
import { openNavView } from "./navHelpers";

const VIEWS = [
  { label: "Portfolio", testId: "portfolio-panel" },
  { label: "Bot", testId: "bot-dashboard" },
  { label: "Backtest", testId: "backtest-run" },
  { label: "Export", testId: "export-hub" },
  { label: "Billing", testId: "billing-dashboard" },
  { label: "Scanner", testId: "scanner-panel" },
  { label: "Settings", testId: "settings-view" },
  { label: "Debug", testId: "debug-log-viewer" },
] as const;

test.describe("live dev smoke", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/");
    await expect(page.getByTestId("status")).toContainText(/API connected|Online/i, {
      timeout: 30_000,
    });
  });

  test("loads portfolio landing with net worth", async ({ page }) => {
    await expect(page.getByTestId("portfolio-panel")).toBeVisible({ timeout: 15_000 });
    await expect(page.getByTestId("net-worth")).toBeVisible();
    await expect(page.locator(".gp-title")).toHaveText("TrendAlgo Bot");
  });

  test("passes accessibility audit on portfolio view", async ({ page }) => {
    await expect(page.getByTestId("portfolio-panel")).toBeVisible({ timeout: 15_000 });
    const results = await new AxeBuilder({ page }).analyze();
    expect(results.violations).toEqual([]);
  });

  test("navigates all primary views without errors", async ({ page }) => {
    await expect(page.getByTestId("portfolio-panel")).toBeVisible({ timeout: 15_000 });

    for (const view of VIEWS) {
      await openNavView(page, view.label);
      await expect(page.getByTestId("mobile-nav")).toBeVisible();
      if (view.testId) {
        await expect(page.getByTestId(view.testId)).toBeVisible({ timeout: 10_000 });
      }
    }
  });

  test("settings tab shows theme and about section", async ({ page }) => {
    await openNavView(page, "Settings");
    await expect(page.getByTestId("settings-view")).toBeVisible();
    await expect(page.getByTestId("settings-panel")).toBeVisible();
    await expect(page.getByTestId("about-panel")).toBeVisible();
    await page.locator("[data-settings-theme]").selectOption("dark");
    await expect(page.locator("html")).toHaveAttribute("data-theme", "dark");
    const results = await new AxeBuilder({ page }).analyze();
    expect(results.violations).toEqual([]);
  });

  test("backtest run produces metrics", async ({ page }) => {
    await openNavView(page, "Backtest");
    await page.getByTestId("backtest-run").click();
    await expect(page.getByTestId("backtest-metrics")).toBeVisible({ timeout: 30_000 });
  });
});
