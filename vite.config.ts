import { defineConfig } from "vite";
import { resolve } from "path";

export default defineConfig({
  build: {
    outDir: "static/js",
    emptyOutDir: true,
    lib: {
      entry: resolve(__dirname, "frontend/src/main.ts"),
      name: "PlaylistGenerator",
      fileName: "app",
      formats: ["iife"],
    },
    sourcemap: true,
    minify: true,
  },
  test: {
    environment: "jsdom",
    include: ["frontend/src/**/*.test.ts"],
  },
});
