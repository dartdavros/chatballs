import { defineConfig, devices } from "@playwright/test";

export default defineConfig({
  testDir: "./tests/e2e",
  timeout: 30_000,
  fullyParallel: true,
  reporter: [["list"], ["html", { open: "never" }]],
  use: {
    trace: "on-first-retry",
  },
  projects: [
    {
      name: "internal-ui",
      use: { ...devices["Desktop Chrome"], baseURL: "http://localhost:5173" },
    },
    {
      name: "checkout",
      use: { ...devices["Desktop Chrome"], baseURL: "http://localhost:5174" },
    },
    {
      name: "web-chat-mobile",
      use: { ...devices["Pixel 7"], baseURL: "http://localhost:5175" },
    },
  ],
});
