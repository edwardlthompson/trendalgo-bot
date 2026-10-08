import process from "node:process";
import { defineConfig } from "vitest/config";
import viteConfig from "./vite.config";

/** Node 25+ installs native Web Storage before jsdom; disable so jsdom owns localStorage. */
const nodeMajor = Number(process.versions.node.split(".")[0] ?? 0);
const workerExecArgv = nodeMajor >= 25 ? ["--no-webstorage"] : [];

export default defineConfig({
  ...viteConfig,
  test: {
    environment: "jsdom",
    exclude: ["e2e/**", "node_modules/**"],
    execArgv: workerExecArgv,
    coverage: {
      provider: "v8",
      include: [
        "src/about/updateChecker.ts",
        "src/about/aboutSession.ts",
        "src/about/donations.ts",
        "src/settings/preferences.ts",
        "src/greet.ts",
      ],
      thresholds: {
        lines: 88,
        functions: 80,
        branches: 78,
        statements: 87,
      },
    },
  },
});
