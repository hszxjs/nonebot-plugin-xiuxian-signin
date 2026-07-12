import { StrictMode } from "react"
import { createRoot } from "react-dom/client"
import { BrowserRouter } from "react-router-dom"

import "antd/dist/reset.css"
import "./index.css"
import App from "./App.tsx"
import { adminBasePath, bootstrapAdminToken } from "@/lib/api.ts"

bootstrapAdminToken()

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <BrowserRouter basename={adminBasePath() || "/"}>
      <App />
    </BrowserRouter>
  </StrictMode>
)
