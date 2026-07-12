import { defineConfig } from "@playwright/test";

export default defineConfig({
  testDir: "./e2e",
  testMatch: "smoke-recommendations.spec.ts",
  timeout: 90_000,
  use: {
    baseURL: "http://127.0.0.1:5173",
    headless: true,
  },
  webServer: undefined,
});
