import type { Page } from "@playwright/test";

/** Primary tabs: Portfolio, Bot, Scanner, Backtest. Everything else is under More. */
const MORE_LABELS = new Set(["Glossary", "Export", "Billing", "Settings", "Debug"]);

export async function openNavView(page: Page, label: string): Promise<void> {
  if (MORE_LABELS.has(label)) {
    await page.getByTestId("nav-more-btn").click();
    await page.getByRole("menuitem", { name: label, exact: true }).click();
    return;
  }
  await page.getByRole("button", { name: label, exact: true }).click();
}
