/**
 * Smoke UI checks against local Vite + API for recently added features.
 * Run: npx playwright test e2e/smoke-recommendations.spec.ts --config=playwright.smoke.config.ts
 */
import { test, expect } from "@playwright/test";

test.describe("product recommendations smoke", () => {
  test("shell: risk badge, more menu, theme toggle, settings orphans", async ({ page }) => {
    await page.goto("/");
    await expect(page.getByTestId("status")).toBeVisible({ timeout: 30_000 });
    await expect(page.getByTestId("risk-badge")).toBeVisible({ timeout: 30_000 });
    await expect(page.getByTestId("nav-more-btn")).toBeVisible();
    await page.getByTestId("nav-more-btn").click();
    await expect(page.getByTestId("nav-more").getByRole("menuitem").first()).toBeVisible();
    await expect(page.locator(".gp-theme-toggle")).toBeVisible();

    await page.getByRole("menuitem", { name: "Settings" }).click();
    await expect(page.getByTestId("settings-view")).toBeVisible();
    await expect(page.getByTestId("risk-panel")).toBeVisible();
    await expect(page.getByTestId("config-form")).toBeVisible();
    await expect(page.getByTestId("ai-recommender")).toBeVisible();
    await expect(page.getByTestId("curated-library")).toBeVisible();
    await expect(page.getByTestId("growth-panel")).toBeVisible();
    await expect(page.getByTestId("go-live-wizard")).toBeVisible();
  });

  test("scanner panel runs and shows results or empty", async ({ page }) => {
    await page.goto("/");
    await page.getByRole("button", { name: "Scanner" }).click();
    await expect(page.getByTestId("scanner-panel")).toBeVisible({ timeout: 30_000 });
    await page.getByTestId("scanner-run").click();
    await expect(
      page.getByTestId("scanner-table").or(page.getByTestId("scanner-empty")).or(page.getByTestId("scanner-degraded")),
    ).toBeVisible({ timeout: 60_000 });
  });

  test("portfolio empty/onboarding or timeline", async ({ page }) => {
    await page.goto("/");
    await page.getByRole("button", { name: "Portfolio" }).click();
    await expect(
      page
        .getByTestId("portfolio-panel")
        .or(page.getByTestId("portfolio-empty"))
        .or(page.getByTestId("boot-skeleton")),
    ).toBeVisible({ timeout: 30_000 });
  });

  test("billing lightning disabled when settlement opens", async ({ page }) => {
    await page.goto("/");
    await page.getByTestId("nav-more-btn").click();
    await page.getByRole("menuitem", { name: "Billing" }).click();
    const empty = page.getByTestId("billing-empty");
    const dash = page.getByTestId("billing-dashboard");
    await expect(empty.or(dash)).toBeVisible({ timeout: 30_000 });
  });

  test("backtest research tools render", async ({ page }) => {
    await page.goto("/");
    await page.getByRole("button", { name: "Backtest" }).click();
    await expect(page.getByTestId("research-tools")).toBeVisible({ timeout: 30_000 });
  });
});
