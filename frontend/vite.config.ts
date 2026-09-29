/// <reference types="vitest/config" />
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

// In development the browser talks to Vite only; /api is proxied to the FastAPI backend
// (override with VITE_API_PROXY_TARGET, e.g. when running inside docker compose).
const target = process.env.VITE_API_PROXY_TARGET ?? "http://127.0.0.1:8000";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    allowedHosts: true,
    proxy: { "/api": { target, changeOrigin: true } },
  },
  preview: {
    port: 4173,
    allowedHosts: true,
    proxy: { "/api": { target, changeOrigin: true } },
  },
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: ["./src/test/setup.ts"],
    css: false,
  },
});
