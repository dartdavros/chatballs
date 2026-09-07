import react from "@vitejs/plugin-react";
import { defineConfig, loadEnv } from "vite";

export default defineConfig(({ mode }) => ({
  plugins: [react()],
  // Панель отдаётся с домена hub под путём /chat/ (nginx).
  base: "/chat/",
  build: {
    rollupOptions: {
      // Два entry: панель чата (iframe) и клиентская страница звонка
      // (nginx: /calls/<token> → /chat/call.html).
      input: {
        main: "index.html",
        call: "call.html",
      },
    },
  },
  server: {
    port: 5175,
    // См. apps/internal-ui/vite.config.ts: опрос файлов в контейнере.
    watch: loadEnv(mode, ".", "").VITE_DEV_POLL ? { usePolling: true, interval: 300 } : undefined,
    host: true,
    allowedHosts: true,
  },
}));
