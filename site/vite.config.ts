import { defineConfig } from "vitest/config";

export default defineConfig({
  publicDir: false,
  build: {
    target: "es2022",
    sourcemap: true,
  },
  test: {
    include: ["tests/**/*.test.ts"],
    environment: "jsdom",
    globals: true,
    setupFiles: ["./tests/setup.ts"],
  },
});
