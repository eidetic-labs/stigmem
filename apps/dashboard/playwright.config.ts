import { defineConfig } from "@playwright/test";

const port = Number(process.env.PLAYWRIGHT_DASHBOARD_PORT ?? "3100");

export default defineConfig({
  testDir: "./tests/e2e",
  fullyParallel: true,
  reporter: process.env.CI
    ? [
        ["list"],
        ["junit", { outputFile: "test-results/playwright-junit.xml" }],
        ["html", { outputFolder: "playwright-report", open: "never" }],
      ]
    : "list",
  use: {
    baseURL: `http://127.0.0.1:${port}`,
    trace: "on-first-retry",
  },
  webServer: {
    command: `corepack pnpm build && corepack pnpm exec next start -H 127.0.0.1 -p ${port}`,
    cwd: __dirname,
    url: `http://127.0.0.1:${port}/login`,
    reuseExistingServer: !process.env.CI,
    env: {
      NEXT_PUBLIC_STIGMEM_API_URL: "http://127.0.0.1:8765",
      SESSION_SECRET: "playwright-session-secret-playwright-session-secret",
    },
  },
});
