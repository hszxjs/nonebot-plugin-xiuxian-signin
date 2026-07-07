import { readFileSync, writeFileSync } from "node:fs";
import { defineConfig, type Plugin } from "vite";
import react from "@vitejs/plugin-react";

function normalizeHtmlNewlines(): Plugin {
  return {
    name: "normalize-html-newlines",
    closeBundle() {
      const htmlPath = new URL("../assets/admin_web/index.html", import.meta.url);
      const html = readFileSync(htmlPath, "utf8");
      writeFileSync(htmlPath, html.replace(/\r\n?/g, "\n"));
    },
  };
}

export default defineConfig({
  plugins: [react(), normalizeHtmlNewlines()],
  base: "./",
  build: {
    outDir: "../assets/admin_web",
    emptyOutDir: true,
  },
});
