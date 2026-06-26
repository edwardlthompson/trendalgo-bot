import { test, expect } from "@playwright/test";
import { mockTrendAlgoApi } from "./apiMock";

test.beforeEach(async ({ page }) => {
  await mockTrendAlgoApi(page);
});

test("renders portfolio as default landing", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByTestId("status")).toContainText("API connected", { timeout: 15_000 });
  await expect(page.getByTestId("portfolio-panel")).toBeVisible();
  await expect(page.getByTestId("net-worth")).toContainText("1500");
});

test("renders dashboard with health widget", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByTestId("status")).toContainText("API connected", { timeout: 15_000 });
  await page.getByRole("button", { name: "Bot" }).click();
  await expect(page.getByTestId("health-widget")).toBeVisible();
  await expect(page.getByTestId("bot-dashboard")).toBeVisible();
});

test("pause all trading from risk panel", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByTestId("status")).toContainText("API connected", { timeout: 15_000 });
  await page.getByRole("button", { name: "Risk" }).click();
  await expect(page.getByTestId("risk-panel")).toBeVisible();
  await page.getByTestId("pause-all").click();
  await expect(page.getByTestId("health-status")).toContainText("Paused");
});

test("runs backtest and shows metrics", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByTestId("status")).toContainText("API connected", { timeout: 15_000 });
  await page.getByRole("button", { name: "Backtest" }).click();
  await page.getByTestId("backtest-run").click();
  await expect(page.getByTestId("backtest-metrics")).toBeVisible();
  await expect(page.getByTestId("equity-chart")).toBeVisible();
});
