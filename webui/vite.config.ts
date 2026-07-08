import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  base: "./",
  build: {
    outDir: "../assets/admin_web",
    emptyOutDir: true,
    rollupOptions: {
      output: {
        manualChunks(id) {
          if (id.includes("node_modules/react") || id.includes("node_modules/react-dom")) {
            return "react-vendor";
          }
          if (id.includes("node_modules/recharts")) {
            return "charts";
          }
          if (
            id.includes("node_modules/d3-") ||
            id.includes("node_modules/victory-vendor") ||
            id.includes("node_modules/decimal.js") ||
            id.includes("node_modules/eventemitter3") ||
            id.includes("node_modules/fast-equals") ||
            id.includes("node_modules/react-transition-group")
          ) {
            return "charts-vendor";
          }
          if (id.includes("node_modules/lucide-react")) {
            return "icons";
          }
        },
      },
    },
  },
});
