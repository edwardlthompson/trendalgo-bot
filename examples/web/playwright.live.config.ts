import { defineConfig, devices } from "@playwright/test";

/** Live smoke — expects API on :8000 and Vite on :5173 already running. */
export default defineConfig({
  testDir: "./e2e",
  testMatch: ["live-smoke.spec.ts", "live-backtest-history.spec.ts", "live-backtest-glossary.spec.ts"],
  fullyParallel: false,
  workers: 1,
  retries: 0,
  timeout: 60_000,
  use: {
    baseURL: process.env.PLAYWRIGHT_BASE_URL ?? "http://127.0.0.1:5173",
    trace: "retain-on-failure",
    serviceWorkers: "block",
  },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
});
