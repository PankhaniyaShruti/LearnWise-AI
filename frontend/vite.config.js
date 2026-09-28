import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react";
import { fileURLToPath } from "node:url";
import { dirname } from "node:path";

const root = dirname(fileURLToPath(import.meta.url));

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, root, "");

  const backend = env.VITE_BACKEND_URL || "http://127.0.0.1:8000";
  const port = Number(env.PORT || 5173);

  return {
    plugins: [react()],
    server: {
      host: "0.0.0.0",
      port,
      proxy: {
        "/api": {
          target: backend,
          changeOrigin: true,
        },
      },
    },
    preview: {
      host: "0.0.0.0",
      port,
      proxy: {
        "/api": {
          target: backend,
          changeOrigin: true,
        },
      },
    },
  };
});