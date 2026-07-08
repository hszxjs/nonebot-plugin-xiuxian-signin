# WebUI Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the embedded admin page with a React + Vite + Tailwind admin console, served from packaged static assets, with a snapshot-based activity dashboard and full page coverage for the existing admin areas.

**Architecture:** Keep `admin.py` as the auth, API, asset, and static-file serving layer. Add a focused dashboard aggregation helper with tests, then build a React SPA in `webui/` and publish its production output to `assets/admin_web/`. Preserve the existing API shapes and convert complex admin data into structured front-end form state.

**Tech Stack:** Python 3.10+, NoneBot/Starlette fallback server, React, TypeScript, Vite, Tailwind CSS, local shadcn-like components, lucide-react icons, Recharts for compact charts.

---

## File Structure

Create:

- `admin_dashboard.py` - pure snapshot aggregation helpers for `/api/dashboard`.
- `tests/test_admin_dashboard.py` - standard-library tests for dashboard aggregation edge cases.
- `webui/package.json` - front-end scripts and dependencies.
- `webui/index.html` - Vite app entry document.
- `webui/tsconfig.json`, `webui/tsconfig.node.json`, `webui/vite.config.ts` - TypeScript and Vite config.
- `webui/tailwind.config.ts`, `webui/postcss.config.cjs` - Tailwind build config.
- `webui/src/main.tsx` - React root.
- `webui/src/App.tsx` - route/page selection and top-level app state.
- `webui/src/styles.css` - Tailwind layers and shadcn-like design tokens.
- `webui/src/lib/api.ts` - token-aware API client.
- `webui/src/lib/types.ts` - shared TypeScript API types.
- `webui/src/lib/format.ts` - number/date/list formatting helpers.
- `webui/src/components/ui/*.tsx` - local UI primitives.
- `webui/src/components/layout/AppShell.tsx` - sidebar, top bar, mobile navigation.
- `webui/src/components/state/*.tsx` - loading, empty, error, and save status views.
- `webui/src/pages/DashboardPage.tsx` - activity and retention command-center page.
- `webui/src/pages/PlayersPage.tsx` - player search and structured record editor.
- `webui/src/pages/ItemsPage.tsx` - item catalog editor.
- `webui/src/pages/BeastCardsPage.tsx` - beast realm card editor.
- `webui/src/pages/EquipmentPage.tsx` - equipment rule editor.
- `webui/src/pages/MysticPage.tsx` - mystic drop editor.
- `webui/src/pages/ConfigPage.tsx` - advanced raw config editor.
- `webui/src/pages/pageShared.ts` - shared page utilities for dirty state and JSON editing.
- `assets/admin_web/` - Vite build output committed with the package.

Modify:

- `admin.py` - import dashboard helper, add `/api/dashboard`, serve `assets/admin_web/`, retain existing APIs and runtime asset routes.
- `pyproject.toml` - include `assets/admin_web/**` patterns in package data.
- `.gitignore` - keep `webui/node_modules/`, `webui/dist/`, and `.superpowers/` untracked.
- `PROJECT_STRUCTURE.md` - document `webui/` source and `assets/admin_web/` runtime build output.
- `README.md` - update web admin description and development/build commands.

Do not revert existing uncommitted changes in `__init__.py`, `admin.py`, or `domain.py`. Before editing those files, inspect their current diff and layer the admin changes on top.

---

### Task 1: Preflight And Working Tree Guard

**Files:**
- Read: `docs/superpowers/specs/2026-07-08-webui-redesign-design.md`
- Read: `admin.py`
- Read: `pyproject.toml`
- Modify later only after diff review: `admin.py`, `pyproject.toml`, `.gitignore`

- [ ] **Step 1: Confirm branch and dirty files**

Run:

```powershell
git status --short
git branch --show-current
git log -3 --oneline
```

Expected:

```text
M __init__.py
M admin.py
M domain.py
?? .superpowers/
```

The exact branch name may differ. Record that the three modified Python files pre-exist this plan.

- [ ] **Step 2: Inspect existing admin changes before editing**

Run:

```powershell
git diff -- admin.py
git diff -- pyproject.toml
git diff -- .gitignore
```

Expected: `admin.py` has current local changes; `pyproject.toml` and `.gitignore` may be clean. Preserve unrelated local edits.

- [ ] **Step 3: Stop the brainstorm companion if it is still running**

Run:

```powershell
Get-Process node -ErrorAction SilentlyContinue | Where-Object { $_.Path -like '*node*' } | Select-Object Id, ProcessName, Path
```

Expected: It is acceptable if no process is listed. If a `server.cjs` brainstorm process is still active and not needed, stop only that process by id after confirming its command line:

```powershell
Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like '*brainstorming*server.cjs*' } | Select-Object ProcessId, CommandLine
Stop-Process -Id <process-id-from-previous-command>
```

- [ ] **Step 4: Commit preflight is not required**

No files should be staged or committed in this task.

---

### Task 2: Dashboard Aggregation Helper And Tests

**Files:**
- Create: `admin_dashboard.py`
- Create: `tests/test_admin_dashboard.py`
- Modify: none

- [ ] **Step 1: Create a pure aggregation helper**

Create `admin_dashboard.py` with this structure:

```python
from __future__ import annotations

from collections import Counter
from datetime import date, datetime
from typing import Any


RECENT_ACTIVE_DAYS = 7
INACTIVE_RISK_DAYS = 14


def parse_record_date(value: Any) -> date | None:
    if not value:
        return None
    text = str(value).strip()
    if not text:
        return None
    for fmt in ("%Y-%m-%d", "%Y/%m/%d"):
        try:
            return datetime.strptime(text[:10], fmt).date()
        except ValueError:
            continue
    return None


def number_value(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def int_value(value: Any, default: int = 0) -> int:
    return int(number_value(value, float(default)))


def player_display_name(record: dict[str, Any], fallback_user_id: str) -> str:
    for key in ("nickname", "name", "user_name"):
        value = str(record.get(key) or "").strip()
        if value:
            return value
    return fallback_user_id


def realm_name(record: dict[str, Any], realm_names: dict[int, str]) -> str:
    index = int_value(record.get("realm_index"), -1)
    if index in realm_names:
        return realm_names[index]
    value = str(record.get("realm") or "").strip()
    return value or "未知境界"


def summarize_player(user_id: str, record: dict[str, Any], today: date, realm_names: dict[int, str]) -> dict[str, Any]:
    last_sign = parse_record_date(record.get("last_sign_date"))
    days_since_sign = (today - last_sign).days if last_sign else None
    return {
        "user_id": user_id,
        "nickname": player_display_name(record, user_id),
        "realm": realm_name(record, realm_names),
        "realm_index": int_value(record.get("realm_index"), -1),
        "battle_power": int_value(record.get("battle_power")),
        "spirit_stones": int_value(record.get("spirit_stones")),
        "last_sign_date": last_sign.isoformat() if last_sign else "",
        "days_since_sign": days_since_sign,
        "signed_today": last_sign == today,
        "recent_active": days_since_sign is not None and 0 <= days_since_sign <= RECENT_ACTIVE_DAYS,
        "inactive_risk": days_since_sign is None or days_since_sign >= INACTIVE_RISK_DAYS,
    }


def build_dashboard_payload(
    users: dict[str, Any],
    today: date,
    realm_names: dict[int, str] | None = None,
) -> dict[str, Any]:
    realm_names = realm_names or {}
    summaries: list[dict[str, Any]] = []
    for user_id, raw in users.items():
        if isinstance(raw, dict):
            summaries.append(summarize_player(str(user_id), raw, today, realm_names))

    total_players = len(summaries)
    signed_today = sum(1 for item in summaries if item["signed_today"])
    recent_active = sum(1 for item in summaries if item["recent_active"])
    inactive_risk = sum(1 for item in summaries if item["inactive_risk"])
    total_stones = sum(int(item["spirit_stones"]) for item in summaries)
    total_power = sum(int(item["battle_power"]) for item in summaries)
    realm_counter = Counter(str(item["realm"]) for item in summaries)

    top_power = sorted(summaries, key=lambda item: int(item["battle_power"]), reverse=True)[:10]
    recent_signins = sorted(
        [item for item in summaries if item["last_sign_date"]],
        key=lambda item: item["last_sign_date"],
        reverse=True,
    )[:12]
    inactive_players = sorted(
        [item for item in summaries if item["inactive_risk"]],
        key=lambda item: item["days_since_sign"] if item["days_since_sign"] is not None else 9999,
        reverse=True,
    )[:12]

    return {
        "ok": True,
        "mode": "snapshot",
        "generated_date": today.isoformat(),
        "metrics": {
            "total_players": total_players,
            "signed_today": signed_today,
            "recent_active": recent_active,
            "inactive_risk": inactive_risk,
            "total_spirit_stones": total_stones,
            "average_spirit_stones": round(total_stones / total_players, 2) if total_players else 0,
            "average_battle_power": round(total_power / total_players, 2) if total_players else 0,
        },
        "realm_distribution": [
            {"realm": realm, "count": count}
            for realm, count in realm_counter.most_common()
        ],
        "top_battle_power": top_power,
        "recent_signins": recent_signins,
        "inactive_players": inactive_players,
        "health_flags": {
            "has_players": total_players > 0,
            "inactive_ratio": round(inactive_risk / total_players, 4) if total_players else 0,
            "today_signin_ratio": round(signed_today / total_players, 4) if total_players else 0,
        },
        "capabilities": {
            "historical_trends": False,
            "snapshot_dashboard": True,
        },
    }
```

- [ ] **Step 2: Add tests for empty and mixed player data**

Create `tests/test_admin_dashboard.py`:

```python
from __future__ import annotations

import importlib.util
from datetime import date
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parents[1] / "admin_dashboard.py"
SPEC = importlib.util.spec_from_file_location("admin_dashboard", MODULE_PATH)
admin_dashboard = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(admin_dashboard)


def test_dashboard_empty_users() -> None:
    payload = admin_dashboard.build_dashboard_payload({}, date(2026, 7, 8), {})

    assert payload["ok"] is True
    assert payload["mode"] == "snapshot"
    assert payload["metrics"]["total_players"] == 0
    assert payload["metrics"]["signed_today"] == 0
    assert payload["realm_distribution"] == []
    assert payload["health_flags"]["has_players"] is False


def test_dashboard_mixed_activity() -> None:
    users = {
        "1001": {
            "nickname": "云舟",
            "realm_index": 3,
            "battle_power": 1200,
            "spirit_stones": 300,
            "last_sign_date": "2026-07-08",
        },
        "1002": {
            "nickname": "眠山",
            "realm_index": 5,
            "battle_power": "2400",
            "spirit_stones": "700",
            "last_sign_date": "2026-06-20",
        },
        "1003": {
            "realm": "散修",
            "battle_power": 100,
            "spirit_stones": 0,
            "last_sign_date": "",
        },
    }

    payload = admin_dashboard.build_dashboard_payload(
        users,
        date(2026, 7, 8),
        {3: "筑基", 5: "金丹"},
    )

    assert payload["metrics"]["total_players"] == 3
    assert payload["metrics"]["signed_today"] == 1
    assert payload["metrics"]["recent_active"] == 1
    assert payload["metrics"]["inactive_risk"] == 2
    assert payload["metrics"]["total_spirit_stones"] == 1000
    assert payload["top_battle_power"][0]["user_id"] == "1002"
    assert payload["recent_signins"][0]["nickname"] == "云舟"
    assert payload["inactive_players"][0]["user_id"] == "1003"
    assert payload["capabilities"]["historical_trends"] is False
```

- [ ] **Step 3: Run tests and confirm they pass**

Run:

```powershell
python -m unittest tests.test_admin_dashboard -v
```

Expected:

```text
test_dashboard_empty_users ... ok
test_dashboard_mixed_activity ... ok
```

- [ ] **Step 4: Commit dashboard helper**

Run:

```powershell
git add admin_dashboard.py tests/test_admin_dashboard.py
git commit -m "feat: add admin dashboard aggregation"
```

Expected: one commit containing only the helper and tests.

---

### Task 3: Serve Dashboard API And React Static Files

**Files:**
- Modify: `admin.py`
- Modify: `pyproject.toml`
- Test: `tests/test_admin_dashboard.py`

- [ ] **Step 1: Add imports and constants in `admin.py`**

Add near existing imports:

```python
from datetime import date
from mimetypes import guess_type

from .admin_dashboard import build_dashboard_payload
```

Add near asset roots:

```python
ADMIN_WEB_ROOT = Path(__file__).parent / "assets" / "admin_web"
ADMIN_WEB_INDEX = ADMIN_WEB_ROOT / "index.html"
ADMIN_WEB_MISSING_HTML = """<!doctype html>
<html lang="zh-CN">
<meta charset="utf-8">
<title>修仙签到后台</title>
<body style="font-family:system-ui,sans-serif;max-width:720px;margin:48px auto;line-height:1.7">
<h1>后台前端尚未构建</h1>
<p>请在仓库根目录执行 <code>npm --prefix webui install</code> 和 <code>npm --prefix webui run build</code>，然后重新访问后台。</p>
</body>
</html>"""
```

- [ ] **Step 2: Add manager method for dashboard payload**

Inside `AdminManager`, add:

```python
    def dashboard_payload(self) -> dict[str, Any]:
        users = self.store.load_users()
        realm_names = {
            int(item["index"]): str(item["name"])
            for item in self.player_meta().get("realms", [])
            if isinstance(item, dict) and "index" in item and "name" in item
        }
        return build_dashboard_payload(users, date.today(), realm_names)
```

If the project already has a configured timezone helper, use that local date instead of `date.today()`.

- [ ] **Step 3: Add static file helpers in `admin.py`**

Add functions near `unauthorized()`:

```python
def admin_web_asset_path(path_text: str = "") -> Path | None:
    if not ADMIN_WEB_INDEX.exists():
        return None
    requested = path_text.strip("/")
    target = ADMIN_WEB_INDEX if not requested else ADMIN_WEB_ROOT / requested
    try:
        resolved = target.resolve()
        root = ADMIN_WEB_ROOT.resolve()
    except OSError:
        return ADMIN_WEB_INDEX
    if root not in resolved.parents and resolved != root:
        return ADMIN_WEB_INDEX
    if resolved.is_file():
        return resolved
    return ADMIN_WEB_INDEX
```

- [ ] **Step 4: Update Starlette routes**

In `install_admin_routes`, replace the page handler body with static file behavior:

```python
    async def page(request: Request) -> Any:
        from starlette.responses import FileResponse, HTMLResponse

        if not authorized(manager, request):
            return HTMLResponse(
                "<html><body><form><h3>修仙签到后台</h3>"
                "<label>管理 Token <input name='token'></label><button>进入</button></form></body></html>"
            )
        asset = admin_web_asset_path(request.path_params.get("asset_path", ""))
        if asset is None:
            return HTMLResponse(ADMIN_WEB_MISSING_HTML, status_code=503)
        return FileResponse(asset)
```

Add dashboard endpoint:

```python
    async def dashboard(request: Request) -> Any:
        if not authorized(manager, request):
            return unauthorized()
        return json_response(manager.dashboard_payload())
```

Add routes:

```python
        (base_path + "/api/dashboard", dashboard, ["GET"]),
        (base_path + "/{asset_path:path}", page, ["GET"]),
```

Keep the existing `(base_path, page, ["GET"])` route.

- [ ] **Step 5: Update fallback HTTP server**

In `_handle_api`, add before the final not-found response:

```python
            if api_path == "/api/dashboard" and method == "GET":
                self._send_json(manager.dashboard_payload())
                return
```

In `_send_page`, serve static HTML when authorized:

```python
        def _send_page(self, query: dict[str, str]) -> None:
            if manager.token and query.get("token", "") != manager.token:
                self._send_html(
                    "<html><body><form><h3>修仙签到后台</h3>"
                    "<label>管理 Token <input name='token'></label><button>进入</button></form></body></html>"
                )
                return
            if not ADMIN_WEB_INDEX.exists():
                self._send_html(ADMIN_WEB_MISSING_HTML, 503)
                return
            body = ADMIN_WEB_INDEX.read_bytes()
            self._send_common_headers("text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
```

Add `_send_admin_web_asset` for asset paths if the fallback server routes nested static files. Use `guess_type(path.name)[0] or "application/octet-stream"` for content type.

- [ ] **Step 6: Include build output in package data**

Modify `pyproject.toml` package data list:

```toml
    "assets/admin_web/*",
    "assets/admin_web/assets/*",
```

- [ ] **Step 7: Run Python checks**

Run:

```powershell
python -m unittest tests.test_admin_dashboard -v
python -m compileall admin.py admin_dashboard.py
```

Expected: tests pass and compileall reports no syntax errors.

- [ ] **Step 8: Commit backend serving changes**

Run:

```powershell
git add admin.py pyproject.toml tests/test_admin_dashboard.py admin_dashboard.py
git commit -m "feat: serve react admin shell"
```

---

### Task 4: Create React/Vite/Tailwind Project Skeleton

**Files:**
- Create: `webui/package.json`
- Create: `webui/index.html`
- Create: `webui/tsconfig.json`
- Create: `webui/tsconfig.node.json`
- Create: `webui/vite.config.ts`
- Create: `webui/tailwind.config.ts`
- Create: `webui/postcss.config.cjs`
- Create: `webui/src/main.tsx`
- Create: `webui/src/App.tsx`
- Create: `webui/src/styles.css`
- Modify: `.gitignore`

- [ ] **Step 1: Create `webui/package.json`**

Use:

```json
{
  "name": "xiuxian-admin-webui",
  "private": true,
  "version": "0.1.0",
  "type": "module",
  "scripts": {
    "dev": "vite --host 127.0.0.1",
    "build": "tsc -b && vite build",
    "preview": "vite preview --host 127.0.0.1",
    "lint": "tsc -b --pretty false"
  },
  "dependencies": {
    "@vitejs/plugin-react": "^5.0.0",
    "class-variance-authority": "^0.7.1",
    "clsx": "^2.1.1",
    "lucide-react": "^0.468.0",
    "react": "^19.0.0",
    "react-dom": "^19.0.0",
    "recharts": "^2.15.0",
    "tailwind-merge": "^2.5.5"
  },
  "devDependencies": {
    "autoprefixer": "^10.4.20",
    "postcss": "^8.4.49",
    "tailwindcss": "^3.4.17",
    "typescript": "^5.7.2",
    "vite": "^6.0.0"
  }
}
```

- [ ] **Step 2: Create Vite and TypeScript config**

`webui/vite.config.ts`:

```ts
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  base: "./",
  build: {
    outDir: "../assets/admin_web",
    emptyOutDir: true,
  },
});
```

`webui/tsconfig.json`:

```json
{
  "compilerOptions": {
    "target": "ES2020",
    "useDefineForClassFields": true,
    "lib": ["DOM", "DOM.Iterable", "ES2020"],
    "allowJs": false,
    "skipLibCheck": true,
    "esModuleInterop": true,
    "allowSyntheticDefaultImports": true,
    "strict": true,
    "forceConsistentCasingInFileNames": true,
    "module": "ESNext",
    "moduleResolution": "Node",
    "resolveJsonModule": true,
    "isolatedModules": true,
    "noEmit": true,
    "jsx": "react-jsx"
  },
  "include": ["src"],
  "references": [{ "path": "./tsconfig.node.json" }]
}
```

`webui/tsconfig.node.json`:

```json
{
  "compilerOptions": {
    "composite": true,
    "module": "ESNext",
    "moduleResolution": "Node",
    "allowSyntheticDefaultImports": true
  },
  "include": ["vite.config.ts"]
}
```

- [ ] **Step 3: Create Tailwind config**

`webui/tailwind.config.ts`:

```ts
import type { Config } from "tailwindcss";

export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        border: "hsl(var(--border))",
        background: "hsl(var(--background))",
        foreground: "hsl(var(--foreground))",
        muted: "hsl(var(--muted))",
        "muted-foreground": "hsl(var(--muted-foreground))",
        card: "hsl(var(--card))",
        "card-foreground": "hsl(var(--card-foreground))",
        primary: "hsl(var(--primary))",
        "primary-foreground": "hsl(var(--primary-foreground))",
        destructive: "hsl(var(--destructive))",
        "destructive-foreground": "hsl(var(--destructive-foreground))"
      },
      borderRadius: {
        lg: "8px",
        md: "6px",
        sm: "4px"
      }
    }
  },
  plugins: []
} satisfies Config;
```

`webui/postcss.config.cjs`:

```js
module.exports = {
  plugins: {
    tailwindcss: {},
    autoprefixer: {},
  },
};
```

- [ ] **Step 4: Create root HTML and CSS**

`webui/index.html`:

```html
<!doctype html>
<html lang="zh-CN">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>修仙签到后台</title>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.tsx"></script>
  </body>
</html>
```

`webui/src/styles.css`:

```css
@tailwind base;
@tailwind components;
@tailwind utilities;

:root {
  --background: 0 0% 98%;
  --foreground: 240 10% 4%;
  --card: 0 0% 100%;
  --card-foreground: 240 10% 4%;
  --muted: 240 5% 96%;
  --muted-foreground: 240 4% 46%;
  --border: 240 6% 90%;
  --primary: 240 6% 10%;
  --primary-foreground: 0 0% 98%;
  --destructive: 0 72% 51%;
  --destructive-foreground: 0 0% 98%;
}

* {
  box-sizing: border-box;
}

body {
  margin: 0;
  min-height: 100vh;
  background: hsl(var(--background));
  color: hsl(var(--foreground));
  font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
}

button,
input,
select,
textarea {
  font: inherit;
}
```

- [ ] **Step 5: Create minimal React entry**

`webui/src/main.tsx`:

```tsx
import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App";
import "./styles.css";

ReactDOM.createRoot(document.getElementById("root") as HTMLElement).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);
```

`webui/src/App.tsx`:

```tsx
export default function App() {
  return (
    <main className="min-h-screen p-6">
      <h1 className="text-2xl font-semibold tracking-normal">修仙签到后台</h1>
      <p className="mt-2 text-sm text-muted-foreground">React admin shell is ready.</p>
    </main>
  );
}
```

- [ ] **Step 6: Update `.gitignore`**

Add:

```gitignore
.superpowers/
webui/node_modules/
webui/dist/
```

- [ ] **Step 7: Install dependencies and build**

Run:

```powershell
npm --prefix webui install
npm --prefix webui run build
```

Expected: `assets/admin_web/index.html` and `assets/admin_web/assets/` are created.

- [ ] **Step 8: Commit front-end skeleton**

Run:

```powershell
git add .gitignore webui assets/admin_web
git commit -m "feat: add react admin webui skeleton"
```

---

### Task 5: API Client, Types, UI Primitives, And Layout Shell

**Files:**
- Create: `webui/src/lib/api.ts`
- Create: `webui/src/lib/types.ts`
- Create: `webui/src/lib/format.ts`
- Create: `webui/src/components/ui/button.tsx`
- Create: `webui/src/components/ui/card.tsx`
- Create: `webui/src/components/ui/input.tsx`
- Create: `webui/src/components/ui/select.tsx`
- Create: `webui/src/components/ui/table.tsx`
- Create: `webui/src/components/ui/badge.tsx`
- Create: `webui/src/components/state/LoadState.tsx`
- Create: `webui/src/components/layout/AppShell.tsx`
- Modify: `webui/src/App.tsx`

- [ ] **Step 1: Create `api.ts`**

```ts
export type ApiOptions = RequestInit & { rawBody?: string };

const TOKEN_KEY = "xiuxianAdminToken";

export function getToken() {
  return localStorage.getItem(TOKEN_KEY) ?? "";
}

export function setToken(token: string) {
  localStorage.setItem(TOKEN_KEY, token.trim());
}

export class ApiError extends Error {
  status: number;

  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

export async function api<T>(path: string, options: ApiOptions = {}): Promise<T> {
  const headers = new Headers(options.headers);
  if (!headers.has("Content-Type") && options.body !== undefined) {
    headers.set("Content-Type", "application/json");
  }
  const token = getToken();
  if (token) {
    headers.set("X-Xiuxian-Token", token);
  }
  const response = await fetch(path, { ...options, headers });
  const text = await response.text();
  const data = text ? JSON.parse(text) : {};
  if (!response.ok) {
    throw new ApiError(response.status, String(data.error || response.statusText));
  }
  return data as T;
}
```

- [ ] **Step 2: Create shared types**

Define the response contracts in `types.ts`:

```ts
export type AdminOk<T> = T & { ok: boolean };

export type PlayerSummary = {
  user_id: string;
  nickname: string;
  realm: string;
  battle_power: number;
  spirit_stones: number;
};

export type DashboardPlayer = PlayerSummary & {
  realm_index: number;
  last_sign_date: string;
  days_since_sign: number | null;
  signed_today: boolean;
  recent_active: boolean;
  inactive_risk: boolean;
};

export type DashboardPayload = AdminOk<{
  mode: "snapshot";
  generated_date: string;
  metrics: {
    total_players: number;
    signed_today: number;
    recent_active: number;
    inactive_risk: number;
    total_spirit_stones: number;
    average_spirit_stones: number;
    average_battle_power: number;
  };
  realm_distribution: Array<{ realm: string; count: number }>;
  top_battle_power: DashboardPlayer[];
  recent_signins: DashboardPlayer[];
  inactive_players: DashboardPlayer[];
  health_flags: {
    has_players: boolean;
    inactive_ratio: number;
    today_signin_ratio: number;
  };
  capabilities: {
    historical_trends: boolean;
    snapshot_dashboard: boolean;
  };
}>;

export type PlayerListPayload = AdminOk<{ players: PlayerSummary[] }>;
export type PlayerDetailPayload = AdminOk<{ record: Record<string, unknown>; meta: PlayerMeta }>;

export type PlayerMeta = {
  realms?: Array<{ index: number; name: string }>;
  attributes?: string[];
  attribute_labels?: Record<string, string>;
  tiers?: string[];
  grades?: string[];
  categories?: string[];
  mystic_types?: string[];
  cultivation_routes?: string[];
  realm_quality_titles?: Record<string, string[]>;
  quality_titles?: string[];
};
```

- [ ] **Step 3: Create formatting helpers**

`format.ts`:

```ts
export function formatNumber(value: number | string | null | undefined) {
  const number = Number(value ?? 0);
  return Number.isFinite(number) ? number.toLocaleString("zh-CN") : "0";
}

export function percent(value: number) {
  return `${Math.round(value * 100)}%`;
}

export function compactDate(value: string | null | undefined) {
  if (!value) return "未记录";
  return value.slice(0, 10);
}
```

- [ ] **Step 4: Create local UI primitives**

For each primitive, export a simple component with `className` merge support. Example `button.tsx`:

```tsx
import { ButtonHTMLAttributes } from "react";
import { twMerge } from "tailwind-merge";

export function Button({ className, ...props }: ButtonHTMLAttributes<HTMLButtonElement>) {
  return (
    <button
      className={twMerge(
        "inline-flex h-9 items-center justify-center gap-2 rounded-md border border-border bg-card px-3 text-sm font-medium shadow-sm transition hover:bg-muted disabled:cursor-not-allowed disabled:opacity-50",
        className,
      )}
      {...props}
    />
  );
}

export function PrimaryButton(props: ButtonHTMLAttributes<HTMLButtonElement>) {
  return <Button {...props} className={twMerge("border-primary bg-primary text-primary-foreground hover:bg-primary/90", props.className)} />;
}
```

Use the same style for Card, Input, Select, Table, and Badge. Keep radius at 8px or less.

- [ ] **Step 5: Create loading, empty, and error states**

`LoadState.tsx`:

```tsx
import { Button } from "../ui/button";

export function LoadingState({ label = "正在载入数据" }: { label?: string }) {
  return <div className="rounded-md border border-border bg-card p-6 text-sm text-muted-foreground">{label}...</div>;
}

export function EmptyState({ title, detail }: { title: string; detail?: string }) {
  return (
    <div className="rounded-md border border-dashed border-border bg-card p-6">
      <div className="font-medium">{title}</div>
      {detail ? <div className="mt-1 text-sm text-muted-foreground">{detail}</div> : null}
    </div>
  );
}

export function ErrorState({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <div className="rounded-md border border-destructive/30 bg-card p-6">
      <div className="text-sm font-medium text-destructive">{message}</div>
      {onRetry ? <Button className="mt-3" onClick={onRetry}>重试</Button> : null}
    </div>
  );
}
```

- [ ] **Step 6: Create layout shell**

`AppShell.tsx`:

```tsx
import { Activity, Boxes, ChartNoAxesCombined, Database, ScrollText, Settings, Shield, Users } from "lucide-react";
import { ReactNode } from "react";
import { Button } from "../ui/button";
import { Input } from "../ui/input";

export type PageKey = "dashboard" | "players" | "items" | "beast" | "equipment" | "mystic" | "config";

const nav = [
  { key: "dashboard", label: "总览", icon: ChartNoAxesCombined },
  { key: "players", label: "玩家档案", icon: Users },
  { key: "items", label: "物品图鉴", icon: Boxes },
  { key: "beast", label: "御兽卡牌", icon: Shield },
  { key: "equipment", label: "灵器规则", icon: Activity },
  { key: "mystic", label: "秘境掉落", icon: ScrollText },
  { key: "config", label: "原始配置", icon: Database },
] as const;

export function AppShell({
  page,
  onPageChange,
  token,
  onTokenChange,
  children,
}: {
  page: PageKey;
  onPageChange: (page: PageKey) => void;
  token: string;
  onTokenChange: (token: string) => void;
  children: ReactNode;
}) {
  return (
    <div className="grid min-h-screen grid-cols-[240px_1fr] bg-background max-lg:grid-cols-1">
      <aside className="border-r border-border bg-card max-lg:hidden">
        <div className="border-b border-border p-4">
          <div className="text-base font-semibold">修仙签到后台</div>
          <div className="text-xs text-muted-foreground">运营指挥台</div>
        </div>
        <nav className="grid gap-1 p-3">
          {nav.map((item) => {
            const Icon = item.icon;
            return (
              <button
                key={item.key}
                className={`flex h-9 items-center gap-2 rounded-md px-3 text-left text-sm ${page === item.key ? "bg-primary text-primary-foreground" : "hover:bg-muted"}`}
                onClick={() => onPageChange(item.key as PageKey)}
              >
                <Icon size={16} />
                {item.label}
              </button>
            );
          })}
        </nav>
      </aside>
      <div className="min-w-0">
        <header className="sticky top-0 z-10 flex items-center justify-between gap-3 border-b border-border bg-background/95 px-4 py-3 backdrop-blur">
          <div className="text-sm text-muted-foreground">React WebUI</div>
          <div className="flex items-center gap-2">
            <Input className="w-56" value={token} onChange={(event) => onTokenChange(event.target.value)} aria-label="管理 Token" />
            <Button type="button">
              <Settings size={16} />
              Token
            </Button>
          </div>
        </header>
        <main className="mx-auto max-w-[1680px] p-4">{children}</main>
      </div>
    </div>
  );
}
```

- [ ] **Step 7: Wire shell in `App.tsx`**

```tsx
import { useState } from "react";
import { AppShell, PageKey } from "./components/layout/AppShell";
import { getToken, setToken } from "./lib/api";

function CurrentPage({ page }: { page: PageKey }) {
  return (
    <section className="rounded-md border border-border bg-card p-6">
      <h1 className="text-xl font-semibold">{page}</h1>
      <p className="mt-2 text-sm text-muted-foreground">页面模块将在后续任务接入。</p>
    </section>
  );
}

export default function App() {
  const [page, setPage] = useState<PageKey>("dashboard");
  const [token, setTokenState] = useState(getToken());

  function updateToken(value: string) {
    setTokenState(value);
    setToken(value);
  }

  return (
    <AppShell page={page} onPageChange={setPage} token={token} onTokenChange={updateToken}>
      <CurrentPage page={page} />
    </AppShell>
  );
}
```

- [ ] **Step 8: Build and commit shell**

Run:

```powershell
npm --prefix webui run build
git add webui assets/admin_web
git commit -m "feat: add admin webui shell"
```

---

### Task 6: Dashboard Page

**Files:**
- Create: `webui/src/pages/DashboardPage.tsx`
- Modify: `webui/src/App.tsx`
- Modify: `webui/src/lib/types.ts`

- [ ] **Step 1: Create Dashboard page with API load states**

`DashboardPage.tsx`:

```tsx
import { useEffect, useState } from "react";
import { Bar, BarChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { ErrorState, LoadingState, EmptyState } from "../components/state/LoadState";
import { Card } from "../components/ui/card";
import { api } from "../lib/api";
import { DashboardPayload } from "../lib/types";
import { compactDate, formatNumber, percent } from "../lib/format";

function MetricCard({ label, value, detail }: { label: string; value: string; detail?: string }) {
  return (
    <Card className="p-4">
      <div className="text-xs text-muted-foreground">{label}</div>
      <div className="mt-2 text-2xl font-semibold tracking-normal">{value}</div>
      {detail ? <div className="mt-1 text-xs text-muted-foreground">{detail}</div> : null}
    </Card>
  );
}

export function DashboardPage() {
  const [data, setData] = useState<DashboardPayload | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  async function load() {
    setLoading(true);
    setError("");
    try {
      setData(await api<DashboardPayload>("/api/dashboard"));
    } catch (err) {
      setError(err instanceof Error ? err.message : "仪表盘载入失败");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void load();
  }, []);

  if (loading) return <LoadingState label="正在载入仪表盘" />;
  if (error) return <ErrorState message={error} onRetry={load} />;
  if (!data || !data.health_flags.has_players) return <EmptyState title="暂无玩家数据" detail="玩家第一次签到后，仪表盘会自动出现活跃与留存信息。" />;

  return (
    <div className="grid gap-4">
      <div>
        <h1 className="text-2xl font-semibold tracking-normal">总览</h1>
        <p className="mt-1 text-sm text-muted-foreground">快照日期 {data.generated_date}，历史趋势将在事件统计接入后启用。</p>
      </div>
      <div className="grid grid-cols-2 gap-3 xl:grid-cols-6">
        <MetricCard label="玩家总数" value={formatNumber(data.metrics.total_players)} />
        <MetricCard label="今日签到" value={formatNumber(data.metrics.signed_today)} detail={percent(data.health_flags.today_signin_ratio)} />
        <MetricCard label="近 7 日活跃" value={formatNumber(data.metrics.recent_active)} />
        <MetricCard label="疑似流失" value={formatNumber(data.metrics.inactive_risk)} detail={percent(data.health_flags.inactive_ratio)} />
        <MetricCard label="平均战力" value={formatNumber(data.metrics.average_battle_power)} />
        <MetricCard label="灵石总量" value={formatNumber(data.metrics.total_spirit_stones)} />
      </div>
      <div className="grid gap-4 xl:grid-cols-[1.2fr_0.8fr]">
        <Card className="p-4">
          <h2 className="font-medium">境界分布</h2>
          <div className="mt-4 h-72">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={data.realm_distribution}>
                <XAxis dataKey="realm" tick={{ fontSize: 12 }} />
                <YAxis allowDecimals={false} tick={{ fontSize: 12 }} />
                <Tooltip />
                <Bar dataKey="count" fill="#18181b" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </Card>
        <Card className="p-4">
          <h2 className="font-medium">战力 Top</h2>
          <div className="mt-3 grid gap-2">
            {data.top_battle_power.slice(0, 8).map((player) => (
              <div key={player.user_id} className="flex items-center justify-between rounded-md border border-border px-3 py-2 text-sm">
                <div>
                  <div className="font-medium">{player.nickname}</div>
                  <div className="text-xs text-muted-foreground">{player.realm}</div>
                </div>
                <div className="font-medium">{formatNumber(player.battle_power)}</div>
              </div>
            ))}
          </div>
        </Card>
      </div>
      <div className="grid gap-4 xl:grid-cols-2">
        <Card className="p-4">
          <h2 className="font-medium">最近签到</h2>
          <div className="mt-3 grid gap-2">
            {data.recent_signins.map((player) => (
              <div key={player.user_id} className="flex items-center justify-between text-sm">
                <span>{player.nickname}</span>
                <span className="text-muted-foreground">{compactDate(player.last_sign_date)}</span>
              </div>
            ))}
          </div>
        </Card>
        <Card className="p-4">
          <h2 className="font-medium">疑似流失</h2>
          <div className="mt-3 grid gap-2">
            {data.inactive_players.map((player) => (
              <div key={player.user_id} className="flex items-center justify-between text-sm">
                <span>{player.nickname}</span>
                <span className="text-muted-foreground">{player.days_since_sign === null ? "未签到" : `${player.days_since_sign} 天`}</span>
              </div>
            ))}
          </div>
        </Card>
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Wire Dashboard page**

In `App.tsx`, import and render:

```tsx
import { DashboardPage } from "./pages/DashboardPage";

function CurrentPage({ page }: { page: PageKey }) {
  if (page === "dashboard") return <DashboardPage />;
  return (
    <section className="rounded-md border border-border bg-card p-6">
      <h1 className="text-xl font-semibold">{page}</h1>
      <p className="mt-2 text-sm text-muted-foreground">页面模块将在后续任务接入。</p>
    </section>
  );
}
```

- [ ] **Step 3: Build and commit Dashboard**

Run:

```powershell
npm --prefix webui run build
git add webui assets/admin_web
git commit -m "feat: add admin activity dashboard"
```

---

### Task 7: Player Records Page And Structured Editors

**Files:**
- Create: `webui/src/pages/PlayersPage.tsx`
- Create: `webui/src/pages/playerEditor.tsx`
- Create: `webui/src/pages/playerMeta.ts`
- Modify: `webui/src/App.tsx`
- Modify: `webui/src/lib/types.ts`

- [ ] **Step 1: Add player editor metadata**

`playerMeta.ts`:

```ts
export const fieldOrder = [
  "user_id",
  "root",
  "acquired_roots",
  "extra_roots",
  "realm_index",
  "realm_exp",
  "total_exp",
  "sign_count",
  "spirit_stones",
  "fishing_chances",
  "pending_fishing",
  "last_sign_date",
  "cultivation_route",
  "rewards",
  "equipped_artifacts",
  "mystic_realm",
  "daily_tasks",
] as const;

export const fieldLabels: Record<string, string> = {
  user_id: "玩家 ID",
  root: "主灵根",
  acquired_roots: "后天灵根",
  extra_roots: "额外灵根",
  realm_index: "境界",
  realm_exp: "当前修为",
  total_exp: "总修为",
  sign_count: "签到次数",
  spirit_stones: "灵石",
  fishing_chances: "垂钓次数",
  pending_fishing: "待结算垂钓",
  last_sign_date: "最近签到",
  cultivation_route: "修炼路线",
  rewards: "背包奖励",
  equipped_artifacts: "已装备灵器",
  mystic_realm: "秘境状态",
  daily_tasks: "每日任务",
};

export const numericFields = new Set(["realm_index", "realm_exp", "total_exp", "sign_count", "spirit_stones", "fishing_chances", "pending_fishing"]);
export const dateFields = new Set(["last_sign_date", "last_encounter_date", "last_bottleneck_date"]);
```

- [ ] **Step 2: Create generic structured editor**

`playerEditor.tsx` should export `PlayerValueEditor` and support scalar, array, and object editing:

```tsx
import { Input } from "../components/ui/input";
import { Button } from "../components/ui/button";
import { Select } from "../components/ui/select";
import { PlayerMeta } from "../lib/types";
import { dateFields, numericFields } from "./playerMeta";

type Path = Array<string | number>;

function cloneValue<T>(value: T): T {
  return JSON.parse(JSON.stringify(value)) as T;
}

function setAtPath(root: Record<string, unknown>, path: Path, value: unknown) {
  const next = cloneValue(root);
  let cursor: Record<string, unknown> | unknown[] = next;
  path.slice(0, -1).forEach((segment) => {
    cursor = (cursor as Record<string, unknown>)[String(segment)] as Record<string, unknown> | unknown[];
  });
  (cursor as Record<string, unknown>)[String(path[path.length - 1])] = value;
  return next;
}

export function PlayerValueEditor({
  label,
  fieldKey,
  value,
  path,
  record,
  meta,
  onChange,
}: {
  label: string;
  fieldKey: string;
  value: unknown;
  path: Path;
  record: Record<string, unknown>;
  meta: PlayerMeta;
  onChange: (record: Record<string, unknown>) => void;
}) {
  function update(nextValue: unknown) {
    onChange(setAtPath(record, path, nextValue));
  }

  if (Array.isArray(value)) {
    return (
      <div className="rounded-md border border-border p-3">
        <div className="mb-2 flex items-center justify-between">
          <div className="text-sm font-medium">{label}</div>
          <Button type="button" onClick={() => update([...value, ""])}>添加</Button>
        </div>
        <div className="grid gap-2">
          {value.map((item, index) => (
            <div key={index} className="grid grid-cols-[1fr_auto] gap-2">
              <PlayerValueEditor label={`${label} ${index + 1}`} fieldKey={fieldKey} value={item} path={[...path, index]} record={record} meta={meta} onChange={onChange} />
              <Button type="button" onClick={() => update(value.filter((_, itemIndex) => itemIndex !== index))}>删除</Button>
            </div>
          ))}
        </div>
      </div>
    );
  }

  if (value && typeof value === "object") {
    const entries = Object.entries(value as Record<string, unknown>);
    return (
      <div className="rounded-md border border-border p-3">
        <div className="mb-2 text-sm font-medium">{label}</div>
        <div className="grid gap-3">
          {entries.map(([key, nested]) => (
            <PlayerValueEditor key={key} label={key} fieldKey={key} value={nested} path={[...path, key]} record={record} meta={meta} onChange={onChange} />
          ))}
        </div>
      </div>
    );
  }

  if (fieldKey === "realm_index") {
    return (
      <label className="grid gap-1 text-sm">
        <span className="text-xs font-medium text-muted-foreground">{label}</span>
        <Select value={String(value ?? "")} onChange={(event) => update(Number(event.target.value))}>
          <option value="">未填写</option>
          {(meta.realms ?? []).map((realm) => <option key={realm.index} value={realm.index}>{realm.index} · {realm.name}</option>)}
        </Select>
      </label>
    );
  }

  if (dateFields.has(fieldKey)) {
    return (
      <label className="grid gap-1 text-sm">
        <span className="text-xs font-medium text-muted-foreground">{label}</span>
        <Input type="date" value={String(value ?? "")} onChange={(event) => update(event.target.value)} />
      </label>
    );
  }

  return (
    <label className="grid gap-1 text-sm">
      <span className="text-xs font-medium text-muted-foreground">{label}</span>
      <Input
        type={numericFields.has(fieldKey) ? "number" : "text"}
        value={String(value ?? "")}
        onChange={(event) => update(numericFields.has(fieldKey) ? Number(event.target.value) : event.target.value)}
      />
    </label>
  );
}
```

- [ ] **Step 3: Create Players page**

`PlayersPage.tsx` loads list, detail, and save:

```tsx
import { useEffect, useMemo, useState } from "react";
import { ErrorState, LoadingState, EmptyState } from "../components/state/LoadState";
import { Button, PrimaryButton } from "../components/ui/button";
import { Card } from "../components/ui/card";
import { Input } from "../components/ui/input";
import { api } from "../lib/api";
import { PlayerDetailPayload, PlayerListPayload, PlayerMeta, PlayerSummary } from "../lib/types";
import { formatNumber } from "../lib/format";
import { PlayerValueEditor } from "./playerEditor";
import { fieldLabels, fieldOrder } from "./playerMeta";

export function PlayersPage() {
  const [players, setPlayers] = useState<PlayerSummary[]>([]);
  const [query, setQuery] = useState("");
  const [selected, setSelected] = useState("");
  const [record, setRecord] = useState<Record<string, unknown> | null>(null);
  const [savedRecord, setSavedRecord] = useState<Record<string, unknown> | null>(null);
  const [meta, setMeta] = useState<PlayerMeta>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);

  const dirty = JSON.stringify(record) !== JSON.stringify(savedRecord);

  async function loadPlayers() {
    setLoading(true);
    setError("");
    try {
      const payload = await api<PlayerListPayload>(`/api/players${query ? `?q=${encodeURIComponent(query)}` : ""}`);
      setPlayers(payload.players ?? []);
    } catch (err) {
      setError(err instanceof Error ? err.message : "玩家列表载入失败");
    } finally {
      setLoading(false);
    }
  }

  async function loadPlayer(userId: string) {
    if (dirty && !window.confirm("当前玩家有未保存修改，确认切换吗？")) return;
    setSelected(userId);
    const payload = await api<PlayerDetailPayload>(`/api/players/${encodeURIComponent(userId)}`);
    setRecord(payload.record ?? {});
    setSavedRecord(payload.record ?? {});
    setMeta(payload.meta ?? {});
  }

  async function save() {
    if (!selected || !record) return;
    setSaving(true);
    try {
      const payload = await api<PlayerDetailPayload>(`/api/players/${encodeURIComponent(selected)}`, {
        method: "PUT",
        body: JSON.stringify(record, null, 2),
      });
      setRecord(payload.record ?? {});
      setSavedRecord(payload.record ?? {});
      await loadPlayers();
    } finally {
      setSaving(false);
    }
  }

  useEffect(() => {
    void loadPlayers();
  }, []);

  const orderedKeys = useMemo(() => {
    if (!record) return [];
    return [...fieldOrder.filter((key) => Object.prototype.hasOwnProperty.call(record, key)), ...Object.keys(record).filter((key) => !fieldOrder.includes(key as never))];
  }, [record]);

  if (loading) return <LoadingState label="正在载入玩家" />;
  if (error) return <ErrorState message={error} onRetry={loadPlayers} />;

  return (
    <div className="grid gap-4 xl:grid-cols-[380px_1fr]">
      <Card className="p-4">
        <div className="flex gap-2">
          <Input value={query} onChange={(event) => setQuery(event.target.value)} />
          <Button onClick={loadPlayers}>搜索</Button>
        </div>
        <div className="mt-4 grid max-h-[calc(100vh-180px)] gap-2 overflow-auto">
          {players.length ? players.map((player) => (
            <button key={player.user_id} onClick={() => void loadPlayer(player.user_id)} className={`rounded-md border border-border p-3 text-left text-sm ${selected === player.user_id ? "bg-muted" : "bg-card"}`}>
              <div className="font-medium">{player.nickname || player.user_id}</div>
              <div className="text-xs text-muted-foreground">{player.realm} · 战力 {formatNumber(player.battle_power)}</div>
            </button>
          )) : <EmptyState title="没有匹配玩家" />}
        </div>
      </Card>
      <Card className="p-4">
        {!record ? <EmptyState title="请选择玩家" detail="从左侧列表选择一个玩家后编辑档案。" /> : (
          <div className="grid gap-4">
            <div className="flex items-center justify-between">
              <div>
                <h1 className="text-xl font-semibold">玩家 {selected}</h1>
                {dirty ? <div className="text-xs text-destructive">有未保存修改</div> : <div className="text-xs text-muted-foreground">已同步</div>}
              </div>
              <div className="flex gap-2">
                <Button onClick={() => setRecord(savedRecord ? JSON.parse(JSON.stringify(savedRecord)) : null)}>撤回修改</Button>
                <PrimaryButton disabled={saving} onClick={save}>{saving ? "保存中" : "保存玩家"}</PrimaryButton>
              </div>
            </div>
            <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
              {orderedKeys.map((key) => (
                <PlayerValueEditor key={key} label={fieldLabels[key] ?? key} fieldKey={key} value={record[key]} path={[key]} record={record} meta={meta} onChange={setRecord} />
              ))}
            </div>
          </div>
        )}
      </Card>
    </div>
  );
}
```

- [ ] **Step 4: Wire Players page in `App.tsx`**

```tsx
import { PlayersPage } from "./pages/PlayersPage";

if (page === "players") return <PlayersPage />;
```

- [ ] **Step 5: Build and commit Players page**

Run:

```powershell
npm --prefix webui run build
git add webui assets/admin_web
git commit -m "feat: add structured player admin page"
```

---

### Task 8: Item Catalog Page

**Files:**
- Create: `webui/src/pages/ItemsPage.tsx`
- Modify: `webui/src/App.tsx`
- Modify: `webui/src/lib/types.ts`

- [ ] **Step 1: Add item types**

Append to `types.ts`:

```ts
export type AdminItem = {
  name: string;
  category?: string;
  tiers?: string[];
  grades?: string[];
  required_realm?: string;
  required_attribute?: string;
  usage?: string;
  source?: string;
  story?: string;
  parameter_note?: string;
  icon?: string;
  customized?: boolean;
};

export type ItemPayload = AdminOk<{
  items: AdminItem[];
  meta: {
    categories?: string[];
    tiers?: string[];
    grades?: string[];
    realms?: string[];
    attributes?: string[];
  };
}>;
```

- [ ] **Step 2: Create Items page**

Use this behavior in `ItemsPage.tsx`:

```tsx
import { useEffect, useMemo, useState } from "react";
import { ErrorState, LoadingState, EmptyState } from "../components/state/LoadState";
import { Button, PrimaryButton } from "../components/ui/button";
import { Card } from "../components/ui/card";
import { Input } from "../components/ui/input";
import { Select } from "../components/ui/select";
import { api, getToken } from "../lib/api";
import { AdminItem, ItemPayload } from "../lib/types";

function iconUrl(icon?: string) {
  if (!icon) return "";
  const token = getToken();
  return `/assets/item-icons/${icon.split("/").map(encodeURIComponent).join("/")}${token ? `?token=${encodeURIComponent(token)}` : ""}`;
}

export function ItemsPage() {
  const [items, setItems] = useState<AdminItem[]>([]);
  const [meta, setMeta] = useState<ItemPayload["meta"]>({});
  const [query, setQuery] = useState("");
  const [category, setCategory] = useState("");
  const [tier, setTier] = useState("");
  const [selectedName, setSelectedName] = useState("");
  const [draft, setDraft] = useState<AdminItem | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  async function load() {
    setLoading(true);
    setError("");
    try {
      const payload = await api<ItemPayload>("/api/items");
      setItems(payload.items ?? []);
      setMeta(payload.meta ?? {});
      const first = payload.items?.[0];
      if (first) {
        setSelectedName(first.name);
        setDraft(first);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "物品图鉴载入失败");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void load();
  }, []);

  const filtered = useMemo(() => items.filter((item) => {
    const text = JSON.stringify(item).toLowerCase();
    return (!query || text.includes(query.toLowerCase())) && (!category || item.category === category) && (!tier || (item.tiers ?? []).includes(tier));
  }).slice(0, 600), [items, query, category, tier]);

  async function save() {
    if (!draft) return;
    const cfg = await api<{ ok: boolean; config: Record<string, unknown> }>("/api/config");
    const config = cfg.config;
    const itemOverrides = typeof config.item_overrides === "object" && config.item_overrides ? config.item_overrides as Record<string, unknown> : {};
    itemOverrides[draft.name] = draft;
    config.item_overrides = itemOverrides;
    await api("/api/config", { method: "PUT", body: JSON.stringify(config, null, 2) });
    await load();
  }

  async function restoreDefault() {
    if (!draft) return;
    const cfg = await api<{ ok: boolean; config: Record<string, unknown> }>("/api/config");
    const config = cfg.config;
    const itemOverrides = typeof config.item_overrides === "object" && config.item_overrides ? config.item_overrides as Record<string, unknown> : {};
    delete itemOverrides[draft.name];
    config.item_overrides = itemOverrides;
    await api("/api/config", { method: "PUT", body: JSON.stringify(config, null, 2) });
    await load();
  }

  if (loading) return <LoadingState label="正在载入物品图鉴" />;
  if (error) return <ErrorState message={error} onRetry={load} />;

  return (
    <div className="grid gap-4 xl:grid-cols-[460px_1fr]">
      <Card className="p-4">
        <div className="grid grid-cols-2 gap-2">
          <Input className="col-span-2" value={query} onChange={(event) => setQuery(event.target.value)} />
          <Select value={category} onChange={(event) => setCategory(event.target.value)}><option value="">全部类别</option>{(meta.categories ?? []).map((value) => <option key={value}>{value}</option>)}</Select>
          <Select value={tier} onChange={(event) => setTier(event.target.value)}><option value="">全部阶级</option>{(meta.tiers ?? []).map((value) => <option key={value}>{value}</option>)}</Select>
        </div>
        <div className="mt-4 grid max-h-[calc(100vh-210px)] gap-2 overflow-auto">
          {filtered.map((item) => (
            <button key={item.name} onClick={() => { setSelectedName(item.name); setDraft(item); }} className={`grid grid-cols-[44px_1fr] gap-3 rounded-md border border-border p-3 text-left ${selectedName === item.name ? "bg-muted" : "bg-card"}`}>
              <div className="grid h-11 w-11 place-items-center overflow-hidden rounded-md border border-border bg-muted">{item.icon ? <img src={iconUrl(item.icon)} className="max-h-10 max-w-10" /> : null}</div>
              <div className="min-w-0 text-sm"><div className="truncate font-medium">{item.name}</div><div className="text-xs text-muted-foreground">{item.category || "未分类"} {item.customized ? "· 已修改" : ""}</div></div>
            </button>
          ))}
        </div>
      </Card>
      <Card className="p-4">
        {!draft ? <EmptyState title="请选择物品" /> : (
          <div className="grid gap-3">
            <div className="flex items-center justify-between">
              <h1 className="text-xl font-semibold">{draft.name}</h1>
              <div className="flex gap-2"><Button onClick={restoreDefault}>恢复默认</Button><PrimaryButton onClick={save}>保存图鉴条目</PrimaryButton></div>
            </div>
            <Input value={draft.category ?? ""} onChange={(event) => setDraft({ ...draft, category: event.target.value })} />
            <textarea className="min-h-24 rounded-md border border-border p-2" value={draft.usage ?? ""} onChange={(event) => setDraft({ ...draft, usage: event.target.value })} />
            <textarea className="min-h-24 rounded-md border border-border p-2" value={draft.source ?? ""} onChange={(event) => setDraft({ ...draft, source: event.target.value })} />
            <textarea className="min-h-32 rounded-md border border-border p-2" value={draft.story ?? ""} onChange={(event) => setDraft({ ...draft, story: event.target.value })} />
          </div>
        )}
      </Card>
    </div>
  );
}
```

- [ ] **Step 3: Wire Items page**

In `App.tsx`:

```tsx
import { ItemsPage } from "./pages/ItemsPage";

if (page === "items") return <ItemsPage />;
```

- [ ] **Step 4: Build and commit Items page**

Run:

```powershell
npm --prefix webui run build
git add webui assets/admin_web
git commit -m "feat: add item catalog admin page"
```

---

### Task 9: Beast Realm Cards Page

**Files:**
- Create: `webui/src/pages/BeastCardsPage.tsx`
- Modify: `webui/src/App.tsx`
- Modify: `webui/src/lib/types.ts`

- [ ] **Step 1: Add beast card types**

Append:

```ts
export type BeastCard = {
  id: string;
  kind: "beast" | "spell";
  name: string;
  realm?: string;
  faction?: string;
  element?: string;
  cost?: number;
  attack?: number;
  defense?: number;
  pool_copies?: number;
  portrait_id?: string;
  icon?: string;
  effect?: string;
  story?: string;
  rules?: unknown;
  customized?: boolean;
};

export type BeastCardPayload = AdminOk<{
  cards: BeastCard[];
  meta: {
    default_pool_copies?: number;
    factions?: string[];
    realms?: Array<{ index: number; name: string }>;
  };
}>;
```

- [ ] **Step 2: Create BeastCards page**

Implement the same load/filter/detail/save pattern as Items, using endpoints:

```ts
const payload = await api<BeastCardPayload>("/api/beast-realm/cards");
const cfg = await api<{ ok: boolean; config: Record<string, unknown> }>("/api/config");
```

Save card overrides under:

```ts
const beastRealm = typeof config.beast_realm === "object" && config.beast_realm ? config.beast_realm as Record<string, unknown> : {};
const overrides = typeof beastRealm.card_overrides === "object" && beastRealm.card_overrides ? beastRealm.card_overrides as Record<string, unknown> : {};
overrides[draft.id] = draft;
beastRealm.card_overrides = overrides;
config.beast_realm = beastRealm;
```

Render:

- filter inputs for search, kind, faction
- card list with name, kind, faction, cost, attack, defense
- detail form for name, realm, faction, cost, attack, defense, pool copies, effect, story
- advanced textarea for `JSON.stringify(draft.rules ?? {}, null, 2)` with parse validation before save

- [ ] **Step 3: Wire BeastCards page**

In `App.tsx`:

```tsx
import { BeastCardsPage } from "./pages/BeastCardsPage";

if (page === "beast") return <BeastCardsPage />;
```

- [ ] **Step 4: Build and commit Beast page**

Run:

```powershell
npm --prefix webui run build
git add webui assets/admin_web
git commit -m "feat: add beast realm card admin page"
```

---

### Task 10: Equipment And Mystic Rules Pages

**Files:**
- Create: `webui/src/pages/EquipmentPage.tsx`
- Create: `webui/src/pages/MysticPage.tsx`
- Modify: `webui/src/App.tsx`
- Modify: `webui/src/lib/types.ts`

- [ ] **Step 1: Add rule payload types**

Append:

```ts
export type EquipmentPayload = AdminOk<{
  rules: Record<string, unknown>;
  meta: {
    realms?: Array<{ index: number; name: string }>;
    tiers?: string[];
    grades?: string[];
    attributes?: string[];
    artifacts?: Array<{ name: string; realm_index: number }>;
  };
}>;

export type MysticPayload = AdminOk<{
  mystic: {
    types?: string[];
    high_risk_types?: string[];
    enabled_types?: string[];
    enabled_high_risk_types?: string[];
    categories?: string[];
    tiers?: string[];
    grades?: string[];
    category_weights?: Record<string, Array<Record<string, unknown>>>;
    drop_overrides?: Record<string, Array<Record<string, unknown>>>;
    fishing_option_rate?: number;
    extra_fishing_chance_rate?: number;
  };
}>;
```

- [ ] **Step 2: Create Equipment page behavior**

`EquipmentPage.tsx` must:

- load `/api/equipment-rules`
- keep `rules` and `meta` in state
- render each realm from `meta.realms`
- edit `rules.artifact_drop_pools[String(realm.index)]`
- row fields: `tier_min`, `tier_max`, `grade`, `attribute`, `name`, `weight`
- save through `/api/config` by setting `config.equipment_rules = rules`

Use this row type:

```ts
type EquipmentRow = {
  tier_min?: string;
  tier_max?: string;
  grade?: string;
  attribute?: string;
  name?: string;
  weight?: number;
};
```

Use this save function:

```ts
async function saveRules(rules: Record<string, unknown>) {
  const payload = await api<{ ok: boolean; config: Record<string, unknown> }>("/api/config");
  payload.config.equipment_rules = rules;
  await api("/api/config", { method: "PUT", body: JSON.stringify(payload.config, null, 2) });
}
```

- [ ] **Step 3: Create Mystic page behavior**

`MysticPage.tsx` must:

- load `/api/mystic`
- call `/api/items` to populate item names for fixed drops
- edit `mystic.fishing_option_rate` and `mystic.extra_fishing_chance_rate` with number inputs `min=0`, `max=1`, `step=0.01`
- render enabled normal and high-risk type checkbox grids
- render category weight rows with category and weight
- render fixed drop rows with category, tier, grade, name, and weight
- save through `/api/config` by setting `config.mystic` and `config.signin.extra_fishing_chance_rate`

Use this save shape:

```ts
config.mystic = {
  enabled_types: mystic.enabled_types ?? [],
  enabled_high_risk_types: mystic.enabled_high_risk_types ?? [],
  category_weights: mystic.category_weights ?? {},
  drop_overrides: mystic.drop_overrides ?? {},
  fishing_option_rate: Number(mystic.fishing_option_rate ?? 0.05),
};
const signin = typeof config.signin === "object" && config.signin ? config.signin as Record<string, unknown> : {};
signin.extra_fishing_chance_rate = Number(mystic.extra_fishing_chance_rate ?? 0.1);
config.signin = signin;
```

- [ ] **Step 4: Wire rule pages**

In `App.tsx`:

```tsx
import { EquipmentPage } from "./pages/EquipmentPage";
import { MysticPage } from "./pages/MysticPage";

if (page === "equipment") return <EquipmentPage />;
if (page === "mystic") return <MysticPage />;
```

- [ ] **Step 5: Build and commit rule pages**

Run:

```powershell
npm --prefix webui run build
git add webui assets/admin_web
git commit -m "feat: add rule configuration admin pages"
```

---

### Task 11: Advanced Config Page And Shared Dirty State

**Files:**
- Create: `webui/src/pages/ConfigPage.tsx`
- Create: `webui/src/pages/pageShared.ts`
- Modify: `webui/src/App.tsx`

- [ ] **Step 1: Add shared JSON utilities**

`pageShared.ts`:

```ts
export function prettyJson(value: unknown) {
  return JSON.stringify(value, null, 2);
}

export function parseJsonObject(text: string) {
  const parsed = JSON.parse(text);
  if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) {
    throw new Error("JSON 必须是对象");
  }
  return parsed as Record<string, unknown>;
}

export function isDirty(current: unknown, saved: unknown) {
  return JSON.stringify(current) !== JSON.stringify(saved);
}
```

- [ ] **Step 2: Create advanced config page**

`ConfigPage.tsx`:

```tsx
import { useEffect, useState } from "react";
import { ErrorState, LoadingState } from "../components/state/LoadState";
import { Button, PrimaryButton } from "../components/ui/button";
import { Card } from "../components/ui/card";
import { api } from "../lib/api";
import { parseJsonObject, prettyJson } from "./pageShared";

export function ConfigPage() {
  const [text, setText] = useState("");
  const [saved, setSaved] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [parseError, setParseError] = useState("");

  async function load() {
    setLoading(true);
    setError("");
    try {
      const payload = await api<{ ok: boolean; config: Record<string, unknown> }>("/api/config");
      const next = prettyJson(payload.config ?? {});
      setText(next);
      setSaved(next);
      setParseError("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "配置载入失败");
    } finally {
      setLoading(false);
    }
  }

  async function save() {
    try {
      const config = parseJsonObject(text);
      await api("/api/config", { method: "PUT", body: prettyJson(config) });
      setSaved(prettyJson(config));
      setParseError("");
    } catch (err) {
      setParseError(err instanceof Error ? err.message : "JSON 解析失败");
    }
  }

  useEffect(() => {
    void load();
  }, []);

  if (loading) return <LoadingState label="正在载入原始配置" />;
  if (error) return <ErrorState message={error} onRetry={load} />;

  return (
    <Card className="grid gap-3 p-4">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold">原始配置</h1>
          <p className="text-sm text-muted-foreground">高级入口。保存前会检查 JSON 是否为对象。</p>
        </div>
        <div className="flex gap-2">
          <Button onClick={() => setText(saved)}>撤回修改</Button>
          <PrimaryButton onClick={save}>保存配置</PrimaryButton>
        </div>
      </div>
      {parseError ? <div className="rounded-md border border-destructive/30 p-3 text-sm text-destructive">{parseError}</div> : null}
      <textarea className="min-h-[calc(100vh-220px)] rounded-md border border-border bg-card p-3 font-mono text-xs" value={text} onChange={(event) => setText(event.target.value)} />
    </Card>
  );
}
```

- [ ] **Step 3: Wire Config page**

In `App.tsx`:

```tsx
import { ConfigPage } from "./pages/ConfigPage";

if (page === "config") return <ConfigPage />;
```

- [ ] **Step 4: Build and commit Config page**

Run:

```powershell
npm --prefix webui run build
git add webui assets/admin_web
git commit -m "feat: add advanced config admin page"
```

---

### Task 12: Visual Polish, Responsiveness, And Navigation Completeness

**Files:**
- Modify: `webui/src/components/layout/AppShell.tsx`
- Modify: `webui/src/styles.css`
- Modify: all page files under `webui/src/pages/`

- [ ] **Step 1: Add mobile navigation fallback**

In `AppShell.tsx`, add a small-screen nav row above main content:

```tsx
<div className="flex gap-2 overflow-x-auto border-b border-border bg-card p-2 lg:hidden">
  {nav.map((item) => (
    <button
      key={item.key}
      className={`shrink-0 rounded-md px-3 py-2 text-sm ${page === item.key ? "bg-primary text-primary-foreground" : "bg-muted"}`}
      onClick={() => onPageChange(item.key as PageKey)}
    >
      {item.label}
    </button>
  ))}
</div>
```

- [ ] **Step 2: Add table overflow guard**

In `styles.css`:

```css
.table-scroll {
  width: 100%;
  overflow-x: auto;
}

.table-scroll table {
  min-width: 760px;
}
```

Wrap dense page tables in `<div className="table-scroll">`.

- [ ] **Step 3: Check text sizing and no overflow**

Run the app:

```powershell
npm --prefix webui run dev
```

Open the URL shown by Vite and check at 390px, 768px, and 1440px widths. Expected: navigation, buttons, inputs, and table content remain inside their containers; data-heavy tables scroll horizontally.

- [ ] **Step 4: Build and commit polish**

Run:

```powershell
npm --prefix webui run build
git add webui assets/admin_web
git commit -m "style: polish admin webui responsiveness"
```

---

### Task 13: Documentation, Package Data, And Verification

**Files:**
- Modify: `README.md`
- Modify: `PROJECT_STRUCTURE.md`
- Modify: `pyproject.toml`
- Read: `assets/admin_web/index.html`

- [ ] **Step 1: Update README web admin section**

Add the development commands:

```markdown
### WebUI 开发

后台前端源码位于 `webui/`，运行时构建产物位于 `assets/admin_web/`。发布包会携带构建产物，插件用户不需要安装 Node。

```bash
npm --prefix webui install
npm --prefix webui run build
python -m compileall .
```
```

- [ ] **Step 2: Update project structure docs**

Add to `PROJECT_STRUCTURE.md`:

```markdown
- `webui/`：React + Vite 后台源码。不要把 `node_modules/` 加入版本控制。
- `assets/admin_web/`：后台前端运行时构建产物，发布包需要读取。
```

- [ ] **Step 3: Confirm package data**

Ensure `pyproject.toml` contains:

```toml
    "assets/admin_web/*",
    "assets/admin_web/assets/*",
```

- [ ] **Step 4: Run full verification**

Run:

```powershell
python -m unittest tests.test_admin_dashboard -v
python -m compileall .
npm --prefix webui run build
git status --short
```

Expected:

- dashboard tests pass
- compileall has no syntax errors
- Vite build writes to `assets/admin_web/`
- `git status --short` does not show `webui/node_modules/` or `.superpowers/`

- [ ] **Step 5: Commit docs and final build metadata**

Run:

```powershell
git add README.md PROJECT_STRUCTURE.md pyproject.toml webui assets/admin_web
git commit -m "docs: document react admin webui"
```

---

## Final Manual Acceptance Checklist

- [ ] Visit `/xiuxian-admin` and see the React shell.
- [ ] Save a token and reload without losing it.
- [ ] Dashboard loads `/api/dashboard` and shows snapshot metrics.
- [ ] Player list search works.
- [ ] Player detail loads and structured fields can be edited without raw JSON.
- [ ] Player repeatable sections support add and delete.
- [ ] Item catalog filters and saves overrides.
- [ ] Beast realm card filters and saves card overrides.
- [ ] Equipment rows add, delete, and save.
- [ ] Mystic probabilities show `0.05` and `0.10` defaults and save correctly.
- [ ] Raw config rejects invalid JSON without losing the typed text.
- [ ] Build assets are present under `assets/admin_web/`.
- [ ] Narrow viewport does not push text or controls outside their containers.


