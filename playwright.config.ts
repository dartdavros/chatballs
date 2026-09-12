import { defineConfig, devices } from "@playwright/test";

export default defineConfig({
  testDir: "./tests/e2e",
  timeout: 30_000,
  fullyParallel: true,
  reporter: [["list"], ["html", { open: "never" }]],
  use: {
    trace: "on-first-retry",
  },
  // Оба проекта должны подниматься сами: web-chat-mobile ходит на :5175, и без
  // второго сервера прогон падал везде, где dev-стек не был поднят заранее.
  webServer: [
    {
      command: "npm --workspace @chatballs/internal-ui run dev",
      url: "http://localhost:5173",
      reuseExistingServer: true,
      timeout: 120_000,
    },
    {
      command: "npm --workspace @chatballs/web-chat run dev",
      url: "http://localhost:5175",
      reuseExistingServer: true,
      timeout: 120_000,
    },
  ],
  projects: [
    {
      name: "internal-ui",
      // Русская локаль браузера: интерфейс открывается на языке установки из
      // моков без перезагрузки, которую иначе делает acceptServerLanguage.
      use: { ...devices["Desktop Chrome"], baseURL: "http://localhost:5173", locale: "ru-RU" },
    },
    {
      name: "web-chat-mobile",
      use: { ...devices["Pixel 7"], baseURL: "http://localhost:5175" },
    },
  ],
});
