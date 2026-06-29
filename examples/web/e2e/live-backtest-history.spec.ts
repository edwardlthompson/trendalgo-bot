/**
 * Live smoke: fleet backtest history visible on Backtest tab.
 * Requires API on :8000 (TRENDALGO_DATA_DIR=data/dev) and Vite on :5173.
 */
import { test, expect } from "@playwright/test";

test("backtest history shows saved Kraken fleet run", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByTestId("status")).toContainText(/API connected|Online/i, {
    timeout: 30_000,
  });
  await page.getByRole("button", { name: "Backtest" }).click();
  await expect(page.getByTestId("backtest-panel")).toBeVisible({ timeout: 15_000 });
  await expect(page.getByTestId("backtest-fleet-history")).toBeVisible({ timeout: 15_000 });
  const historyCard = page.getByTestId("fleet-history-fcf9a93a588c");
  await expect(historyCard).toBeVisible({ timeout: 15_000 });
  await expect(historyCard).toContainText(/CDLHARAMICROSS/i);
  await expect(page.getByTestId("backtest-fleet-top10")).toBeVisible({ timeout: 15_000 });
  await expect(page.getByTestId("backtest-buy-hold-row")).toBeVisible();
  await expect(page.getByTestId("backtest-create-bot-0")).toBeVisible();
});
