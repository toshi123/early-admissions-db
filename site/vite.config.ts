import { defineConfig } from "vitest/config";

export default defineConfig(({ command }) => ({
  publicDir: command === "serve" ? "public" : false,
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
}));
