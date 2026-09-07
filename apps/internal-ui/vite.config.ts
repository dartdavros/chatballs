import react from "@vitejs/plugin-react";
import { defineConfig, loadEnv } from "vite";

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, ".", "");
  const devApiTarget = env.VITE_DEV_API_TARGET;

  return {
    plugins: [react()],
    build: {
      rollupOptions: {
        output: {
          manualChunks(id) {
            if (!id.includes("node_modules")) return undefined;
            if (
              id.includes("/react/")
              || id.includes("/react-dom/")
              || id.includes("/scheduler/")
            ) return "vendor-react";
            if (
              id.includes("/antd/")
              || id.includes("@ant-design/")
              || id.includes("/rc-")
              || id.includes("/dayjs/")
            ) return "vendor-ui";
            return undefined;
          },
        },
      },
    },
    server: {
      port: 5173,
      // Под Docker на Windows bind-mount не пробрасывает inotify внутрь
      // контейнера, и vite не видит правок — HMR молчит до ручной перезагрузки.
      // Опрос включается только в контейнере (переменная задана в compose.dev).
      watch: env.VITE_DEV_POLL ? { usePolling: true, interval: 300 } : undefined,
      proxy: devApiTarget
        ? {
            "/api": { target: devApiTarget, changeOrigin: false },
            "/ws": { target: devApiTarget, changeOrigin: false, ws: true },
          }
        : undefined,
    },
  };
});
