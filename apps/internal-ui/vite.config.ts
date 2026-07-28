import react from "@vitejs/plugin-react";
import { defineConfig, loadEnv } from "vite";

export default defineConfig(({ mode }) => {
  const devApiTarget = loadEnv(mode, ".", "").VITE_DEV_API_TARGET;

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
      proxy: devApiTarget
        ? {
            "/api": { target: devApiTarget, changeOrigin: false },
            "/ws": { target: devApiTarget, changeOrigin: false, ws: true },
          }
        : undefined,
    },
  };
});
