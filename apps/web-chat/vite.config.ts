import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

export default defineConfig({
  plugins: [react()],
  // Панель отдаётся с домена hub под путём /chat/ (nginx).
  base: "/chat/",
  server: {
    port: 5175,
    host: true,
    allowedHosts: true,
  },
});
