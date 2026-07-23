import react from "@vitejs/plugin-react";
import { defineConfig, loadEnv } from "vite";

export default defineConfig(({ mode }) => {
  const devApiTarget = loadEnv(mode, ".", "").VITE_DEV_API_TARGET;

  return {
    plugins: [react()],
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
