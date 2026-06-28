/**
 * Live smoke against running dev stack (API :8000 + Vite :5173).
 * Run: npx playwright test e2e/live-smoke.spec.ts --config=playwright.live.config.ts
 */
import { test, expect } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";

const VIEWS = [
  { label: "Portfolio", testId: "portfolio-panel" },
  { label: "Bot", testId: "bot-dashboard" },
  { label: "Backtest", testId: "backtest-run" },
  { label: "Export", testId: "export-hub" },
  { label: "Billing", testId: "billing-dashboard" },
  { label: "Scanner", testId: "scanner-panel" },
  { label: "Risk", testId: "risk-panel" },
  { label: "Config", testId: "config-form" },
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
      await page.getByRole("button", { name: view.label, exact: true }).click();
      await expect(page.getByTestId("mobile-nav")).toBeVisible();
      if (view.testId) {
        await expect(page.getByTestId(view.testId)).toBeVisible({ timeout: 10_000 });
      }
    }
  });

  test("settings panel opens and theme toggle works", async ({ page }) => {
    await page.getByRole("button", { name: "Settings" }).click();
    await expect(page.getByTestId("settings-panel")).toBeVisible();
    await page.locator("[data-settings-theme]").selectOption("dark");
    await expect(page.locator("html")).toHaveAttribute("data-theme", "dark");
    const results = await new AxeBuilder({ page }).analyze();
    expect(results.violations).toEqual([]);
  });

  test("about panel opens with version", async ({ page }) => {
    await page.getByRole("button", { name: "About" }).click();
    await expect(page.getByTestId("about-panel")).toBeVisible();
    await expect(page.getByTestId("about-status")).toBeVisible();
    const results = await new AxeBuilder({ page }).analyze();
    expect(results.violations).toEqual([]);
  });

  test("risk pause and resume round-trip", async ({ page }) => {
    await page.getByRole("button", { name: "Risk" }).click();
    await expect(page.getByTestId("risk-panel")).toBeVisible();
    await page.getByTestId("pause-all").click();
    await page.getByRole("button", { name: "Portfolio" }).click();
    await expect(page.getByTestId("health-widget")).toBeVisible({ timeout: 10_000 });
    await expect(page.getByTestId("health-status")).toContainText(/Paused/i, { timeout: 10_000 });
    await page.getByRole("button", { name: "Risk" }).click();
    await page.getByTestId("resume-trading").click();
    await page.getByRole("button", { name: "Portfolio" }).click();
    await expect(page.getByTestId("health-status")).not.toContainText(/Paused/i, { timeout: 10_000 });
  });

  test("backtest run produces metrics", async ({ page }) => {
    await page.getByRole("button", { name: "Backtest" }).click();
    await page.getByTestId("backtest-run").click();
    await expect(page.getByTestId("backtest-metrics")).toBeVisible({ timeout: 30_000 });
  });
});
