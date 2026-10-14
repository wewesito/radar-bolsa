import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

// Puerto fijo: Tauri carga esta URL en desarrollo (ver src-tauri/tauri.conf.json).
export default defineConfig({
  plugins: [react()],
  clearScreen: false,
  server: { port: 1420, strictPort: true, host: "127.0.0.1" },
  build: { target: "safari16", outDir: "dist" },
});
