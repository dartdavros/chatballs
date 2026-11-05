import react from "@vitejs/plugin-react";
import { loadEnv } from "vite";
import { defineConfig } from "vitest/config";

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, ".", "");
  const devApiTarget = env.VITE_DEV_API_TARGET;
  return {
    plugins: [react()],
    test: { css: { include: [/widget\.css/] } },
    // Панель отдаётся с домена установки под путём /chat/ (nginx).
    base: "/chat/",
    build: {
      rollupOptions: {
        // Два entry: панель чата (iframe) и клиентская страница звонка
        // (nginx: /calls/<token> → /chat/call.html).
        input: {
          main: "index.html",
          call: "call.html",
          rating: "rating.html",
        },
      },
    },
    server: {
      port: 5175,
      // См. apps/internal-ui/vite.config.ts: опрос файлов в контейнере.
      watch: env.VITE_DEV_POLL ? { usePolling: true, interval: 1000 } : undefined,
      proxy: devApiTarget ? {
        "/api": { target: devApiTarget, changeOrigin: false },
        "/chat-widget.js": { target: devApiTarget, changeOrigin: false },
      } : undefined,
      host: true,
      allowedHosts: true,
    },
  };
});
