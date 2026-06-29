/**
 * Live smoke: backtest strategy link opens filtered glossary entry.
 * Requires API on :8000 (TRENDALGO_DATA_DIR=data/dev) and Vite on :5173.
 */
import { test, expect } from "@playwright/test";

test("backtest strategy opens single glossary entry", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByTestId("status")).toContainText(/API connected|Online/i, {
    timeout: 30_000,
  });
  await page.getByRole("button", { name: "Backtest" }).click();
  await expect(page.getByTestId("backtest-fleet-top10")).toBeVisible({ timeout: 15_000 });

  const strategyLink = page
    .getByTestId("backtest-fleet-top10")
    .getByTestId("backtest-strategy-link-CDLHARAMICROSS");
  await expect(strategyLink).toBeVisible();
  await strategyLink.click();

  await expect(page.getByTestId("ta-glossary-page")).toBeVisible({ timeout: 15_000 });
  await expect(page.getByTestId("ta-glossary-page-search")).toHaveValue("CDLHARAMICROSS");
  await expect(page.getByTestId("ta-glossary-CDLHARAMICROSS")).toBeVisible();
  await expect(page.getByTestId("ta-glossary-show-all")).toBeVisible();

  const cards = page.locator(".gp-ta-glossary-card");
  await expect(cards).toHaveCount(1);

  await expect
    .poll(async () => page.evaluate(() => window.location.hash))
    .toMatch(/ta-glossary-cdlharamicross/i);

  await page.getByTestId("ta-glossary-show-all").click();
  await expect(cards).not.toHaveCount(1);
  await expect(page.getByTestId("ta-glossary-page-search")).toHaveValue("");
});
