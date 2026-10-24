import { defineConfig, devices } from "@playwright/test";
export default defineConfig({
  testDir: "./e2e",
  timeout: 30000,
  fullyParallel: false,
  use: {
    baseURL: process.env.APP_URL ?? "http://localhost:8080",
    screenshot: "only-on-failure",
    trace: "retain-on-failure",
  },
  projects: [{ name: "desktop", use: { ...devices["Desktop Chrome"] } }],
  reporter: "list",
});
