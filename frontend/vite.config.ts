import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  base: "./",
  build: {
    outDir: "../src/qualityscaler/webview/assets",
    emptyOutDir: true,
  },
  test: {
    environment: "node",
    include: ["tests/**/*.test.ts"],
  },
});
