import path from "node:path"
import react from "@vitejs/plugin-react"
import { defineConfig } from "vitest/config"

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  build: {
    // 运行时由 admin.py 的 ADMIN_WEB_ROOT 加载：
    // nonebot_plugin_xiuxian_signin/assets/admin_web/。
    // webui/ 与 nonebot_plugin_xiuxian_signin/ 同级，故需回退一层再进入包目录。
    outDir: "../nonebot_plugin_xiuxian_signin/assets/admin_web",
    emptyOutDir: true,
    rollupOptions: {
      output: {
        manualChunks(id) {
          if (!id.includes("node_modules")) {
            return undefined
          }
          if (
            id.includes("/react/") ||
            id.includes("/react-dom/") ||
            id.includes("/react-router") ||
            id.includes("/scheduler/")
          ) {
            return "react-vendor"
          }
          if (
            id.includes("/antd/") ||
            id.includes("/@ant-design/icons/") ||
            id.includes("/rc-")
          ) {
            return "antd-vendor"
          }
          if (id.includes("/@ant-design/charts/") || id.includes("/@antv/")) {
            return "charts-vendor"
          }
          if (id.includes("/ky/") || id.includes("/swr/")) {
            return "data-vendor"
          }
          return undefined
        },
      },
    },
  },
  test: {
    environment: "jsdom",
    setupFiles: ["./src/test/setup.ts"],
  },
})
