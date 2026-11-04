import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";
import { env } from "node:process";

export default defineConfig({
  plugins: [react()],
  server: {
    host: "127.0.0.1",
    port: 5173,
    proxy: { "/api": env.PV3D_API_URL || "http://127.0.0.1:8000" },
  },
  test: {
    environment: "jsdom",
    setupFiles: ["./src/test/setup.ts"],
    clearMocks: true,
    // Interaction-heavy tests exceed the 5 s default when files run in parallel on
    // small CI runners; the per-step waitFor timeouts inside the tests stay strict.
    testTimeout: 20_000,
    hookTimeout: 20_000,
    // One worker per file starves interaction-heavy tests on 2-4 core runners;
    // bound the parallelism instead of loosening assertions.
    maxWorkers: 2,
  },
});
