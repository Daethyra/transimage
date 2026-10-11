import { defineConfig } from "vite";

export default defineConfig({
  base: "/transimage",
  build: { target: "es2022" },
  optimizeDeps: { exclude: ["@ffmpeg/ffmpeg", "@ffmpeg/util"] },
  assetsInclude: ["**/*.wasm"],
});
