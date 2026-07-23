import { StrictMode } from "react"
import { createRoot } from "react-dom/client"
import { BrowserRouter } from "react-router-dom"

import "antd/dist/reset.css"
import "./index.css"
import { adminBasePath, bootstrapAdminToken } from "@/lib/api.ts"
import App from "./App.tsx"

bootstrapAdminToken()

const rootElement = document.getElementById("root")

if (!rootElement) {
  throw new Error('Root element "#root" was not found')
}

createRoot(rootElement).render(
  <StrictMode>
    <BrowserRouter basename={adminBasePath() || "/"}>
      <App />
    </BrowserRouter>
  </StrictMode>,
)
