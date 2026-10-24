import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";
const apiTarget = process.env.API_TARGET ?? "http://localhost:8000";
export default defineConfig({
  test: { include: ["src/**/*.test.ts"] },
  plugins: [react(), tailwindcss()],
  build: {
    rollupOptions: {
      output: {
        manualChunks: { charts: ["recharts"], flow: ["@xyflow/react"] },
      },
    },
  },
  server: {
    proxy: {
      "/api": apiTarget,
      "/docs": apiTarget,
      "/openapi.json": apiTarget,
    },
  },
});
