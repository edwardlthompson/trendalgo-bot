import { test, expect } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";
import { mockTrendAlgoApi } from "./apiMock";
import { openNavView } from "./navHelpers";
import type { Page } from "@playwright/test";

async function mockUpdateEndpoints(page: Page): Promise<void> {
  await page.route("**/app-update.json", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        release_repo: "test-owner/test-repo",
        installed_artifact_format: "pwa",
      }),
    });
  });
  await page.route("**/repos/test-owner/test-repo/releases/latest", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ tag_name: "v99.0.0" }),
    });
  });
}

test.beforeEach(async ({ page }) => {
  await page.addInitScript(() => {
    localStorage.setItem("trendalgo.onboarding.dismissed", "1");
  });
  await mockTrendAlgoApi(page);
});

test("renders TrendAlgo heading", async ({ page }) => {
  await page.goto("/");
  await expect(page.locator(".gp-title")).toHaveText("TrendAlgo Bot");
  await expect(page.getByTestId("status")).toContainText("API connected", { timeout: 15_000 });
  await expect(page.getByTestId("portfolio-panel")).toBeVisible({ timeout: 15_000 });
});

test("passes accessibility audit", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByTestId("portfolio-panel")).toBeVisible({ timeout: 15_000 });
  const results = await new AxeBuilder({ page }).analyze();
  expect(results.violations).toEqual([]);
});

test("passes accessibility audit on settings tab", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByTestId("portfolio-panel")).toBeVisible({ timeout: 15_000 });
  await openNavView(page, "Settings");
  await expect(page.getByTestId("settings-view")).toBeVisible();
  const results = await new AxeBuilder({ page }).analyze();
  expect(results.violations).toEqual([]);
});

test("homepage visual snapshot", async ({ page }) => {
  test.skip(!!process.env.CI, "Visual baseline is captured on local Chromium; Linux CI fonts differ");
  await page.goto("/");
  await expect(page.locator("main")).toBeVisible();
  await expect(page).toHaveScreenshot("homepage.png", { maxDiffPixelRatio: 0.02 });
});

test("settings tab shows preferences, theme, and about", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByTestId("status")).toContainText("API connected", { timeout: 15_000 });
  await openNavView(page, "Settings");
  await expect(page.getByTestId("settings-view")).toBeVisible();
  await expect(page.getByRole("heading", { name: "Settings" })).toBeVisible();
  await expect(page.getByTestId("settings-panel")).toBeVisible();
  await expect(page.getByRole("heading", { name: "About" })).toBeVisible();
  await expect(page.getByTestId("about-panel")).toBeVisible();
  await page.locator("[data-settings-theme]").selectOption("dark");
  await expect(page.locator("html")).toHaveAttribute("data-theme", "dark");
});

test("persists dark theme after reload", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByTestId("status")).toContainText("API connected", { timeout: 15_000 });
  await openNavView(page, "Settings");
  await page.locator("[data-settings-theme]").selectOption("dark");
  await expect(page.locator("html")).toHaveAttribute("data-theme", "dark");
  await page.reload();
  await expect(page.locator("html")).toHaveAttribute("data-theme", "dark");
});

test("toggles update check in settings", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByTestId("status")).toContainText("API connected", { timeout: 15_000 });
  await openNavView(page, "Settings");
  const toggle = page.locator("[data-settings-update]");
  await expect(toggle).not.toBeChecked();
  await toggle.check();
  await expect(toggle).toBeChecked();
});

test("changes display currency preference", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByTestId("status")).toContainText("API connected", { timeout: 15_000 });
  await openNavView(page, "Settings");
  await page.locator("[data-settings-currency]").selectOption("EUR");
  await expect(page.locator("[data-settings-currency]")).toHaveValue("EUR");
  await page.reload();
  await expect(page.getByTestId("status")).toContainText("API connected", { timeout: 15_000 });
  await openNavView(page, "Settings");
  await expect(page.locator("[data-settings-currency]")).toHaveValue("EUR");
});

test.describe("update status", () => {
  test.use({ serviceWorkers: "block" });

  test("shows update status in about after enabling update check", async ({ page }) => {
  await mockUpdateEndpoints(page);

  await page.goto("/");
  await expect(page.getByTestId("status")).toContainText("API connected", { timeout: 15_000 });
  await openNavView(page, "Settings");
  await expect(page.getByTestId("about-status")).toContainText("latest version");

  await page.locator("[data-settings-update]").check();
  await page.waitForResponse(/releases\/latest/);
  const status = page.getByTestId("about-status");
  await expect(status).toBeVisible();
  await expect(status).toContainText("Update available");
  await expect(status).toContainText("99.0.0");
  await expect(status).not.toContainText("latest version");
  });
});

test.describe("PWA apply update", () => {
  test.use({ serviceWorkers: "block" });

  test("shows apply button when update is available", async ({ page }) => {
    await mockUpdateEndpoints(page);

    await page.goto("/");
    await expect(page.getByTestId("status")).toContainText("API connected", { timeout: 15_000 });
    await openNavView(page, "Settings");
    await page.locator("[data-settings-update]").check();
    await page.waitForResponse(/releases\/latest/);
    await expect(page.getByTestId("about-apply")).toBeVisible();
    await expect(page.getByTestId("about-apply")).toBeEnabled();
  });

  test("clears restart guard on load", async ({ page }) => {
    await page.addInitScript(() => {
      localStorage.setItem("gp-update-restart-pending", "true");
    });
    await page.goto("/");
    const pending = await page.evaluate(() =>
      localStorage.getItem("gp-update-restart-pending"),
    );
    expect(pending).toBeNull();
  });
});

test.describe("home update banner", () => {
  test.use({ serviceWorkers: "block" });

  test("shows update status on home when check finds newer version", async ({ page }) => {
    await mockUpdateEndpoints(page);

    await page.goto("/");
    await expect(page.getByTestId("status")).toContainText("API connected", { timeout: 15_000 });
    await openNavView(page, "Settings");
    await page.locator("[data-settings-update]").check();
    await page.waitForResponse(/releases\/latest/);
    await expect(page.getByTestId("home-update-status")).toContainText("Update available");
    await expect(page.getByTestId("home-update-status")).toContainText("99.0.0");
  });
});

test.describe("portfolio performance chart", () => {
  const ranges = ["1y", "6m", "3m", "1m", "14d", "7d", "24h"] as const;

  test("fills chart host width for every time range", async ({ page }) => {
    test.setTimeout(60_000);
    await page.goto("/");
    await expect(page.getByTestId("portfolio-panel")).toBeVisible({ timeout: 15_000 });
    await expect(page.getByTestId("performance-range-1y")).toBeVisible({ timeout: 15_000 });

    for (const range of ranges) {
      if (range !== "1y") {
        const response = page.waitForResponse(
          (resp) => resp.url().includes(`/portfolio/performance?range=${range}`) && resp.ok(),
        );
        await page.getByTestId(`performance-range-${range}`).click();
        await response;
      }
      await expect(page.getByTestId(`performance-range-${range}`)).toHaveClass(/gp-range-btn-active/);
      await page.waitForFunction(() => {
        const host = document.querySelector("[data-testid=portfolio-equity-chart]");
        const table = host?.querySelector("table");
        return (table?.clientWidth ?? 0) > 280;
      });

      const widths = await page.evaluate(() => {
        const host = document.querySelector("[data-testid=portfolio-equity-chart]");
        const table = host?.querySelector("table");
        return {
          host: host?.clientWidth ?? 0,
          table: table?.clientWidth ?? 0,
        };
      });

      expect(widths.host).toBeGreaterThan(280);
      expect(widths.table).toBeGreaterThanOrEqual(Math.floor(widths.host * 0.95));
    }
  });
});

test.describe("offline shell", () => {
  test("shows offline status when connectivity drops", async ({ page, context }) => {
    await mockTrendAlgoApi(page);
    await page.goto("/");
    await expect(page.getByTestId("status")).toContainText("API connected", { timeout: 15_000 });
    await expect(page.getByTestId("portfolio-panel")).toBeVisible({ timeout: 15_000 });
    await context.setOffline(true);
    await page.evaluate(() => window.dispatchEvent(new Event("offline")));
    await expect(page.getByTestId("status")).toContainText(/Offline|cached/i, { timeout: 5_000 });
    await expect(page.getByTestId("portfolio-panel")).toBeVisible();
  });
});
