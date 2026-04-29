import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  build: {
    outDir: "dist",
    emptyOutDir: true,
  },
  server: {
    port: 5173,
    proxy: {
      // Proxy all /api calls to the FastAPI backend during development
      "/api": {
        target: "http://localhost:8321",
        changeOrigin: true,
      },
      // Proxy manifest and icon endpoints
      "/manifest.webmanifest": {
        target: "http://localhost:8321",
        changeOrigin: true,
      },
      "/icon.svg": {
        target: "http://localhost:8321",
        changeOrigin: true,
      },
    },
  },
});
