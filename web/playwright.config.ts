import { defineConfig, devices } from "@playwright/test";

// The prototype's own server, built and started for the run. Engines follow
// DD_ENGINES like the api's player tests (Firefox runs in CI).
const engines = (process.env.DD_ENGINES ?? "chromium,webkit").split(",");
const PORT = 3217;

export default defineConfig({
  testDir: "e2e",
  timeout: 90_000,
  use: { baseURL: `http://localhost:${PORT}` },
  webServer: {
    command: `NEXT_DIST_DIR=.next-e2e pnpm build && NEXT_DIST_DIR=.next-e2e pnpm start -p ${PORT}`,
    url: `http://localhost:${PORT}`,
    timeout: 180_000,
    reuseExistingServer: false,
  },
  projects: engines.map((name) => ({
    name,
    use: { ...(name === "firefox" ? devices["Desktop Firefox"] : name === "webkit" ? devices["Desktop Safari"] : devices["Desktop Chrome"]) },
  })),
});
