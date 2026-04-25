import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  base: "/app/",
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/api": {
        target: "http://127.0.0.1:8765",
        changeOrigin: true
      },
      "/upload": {
        target: "http://127.0.0.1:8765",
        changeOrigin: true
      },
      "/runs": {
        target: "http://127.0.0.1:8765",
        changeOrigin: true
      },
      "/chart": {
        target: "http://127.0.0.1:8765",
        changeOrigin: true
      }
    }
  }
});
