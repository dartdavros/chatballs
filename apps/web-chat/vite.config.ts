import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

export default defineConfig({
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
    host: true,
    allowedHosts: true,
  },
});
