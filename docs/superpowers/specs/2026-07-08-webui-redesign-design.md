# WebUI Redesign Design

Date: 2026-07-08

## Goal

Replace the current embedded `admin.py` web UI with a user-friendly, observable, shadcn-like admin console. The new console should make player activity and retention visible on the home page, then provide full management coverage for every existing admin area: player records, item catalog, beast realm cards, equipment rules, mystic realm drops, and raw configuration.

## Current Context

The plugin is a single NoneBot package rooted at `nonebot_plugin_xiuxian_signin`. The current admin UI lives inside `admin.py` as a large `ADMIN_HTML` string containing HTML, CSS, and JavaScript. `admin.py` also exposes the API endpoints and has a fallback built-in HTTP server path. Existing API coverage includes config, players, item catalog, beast realm cards, equipment rules, mystic realm config, backups, and asset serving for portraits/icons.

The repository already has runtime asset conventions documented in `PROJECT_STRUCTURE.md`: runtime files live under `assets/`, generated previews and temporary build outputs should stay out of the package, and package data is controlled by `pyproject.toml`.

## Decisions

- Build a React + Vite + Tailwind front end with shadcn-like local components.
- Use a full SPA replacement for all current admin pages in v1.
- Commit front-end source under `webui/`.
- Commit Vite production output under `assets/admin_web/`, so plugin users do not need Node or npm after installation.
- Keep existing admin APIs compatible where possible.
- Add only focused aggregation endpoints for the new dashboard and future stats expansion.
- Use the "command center" dashboard direction: side navigation, compact key metrics, charts/lists, risk highlights, and quick action tiles.
- Prioritize player activity and retention on the dashboard.
- Use a two-stage observability model: v1 derives dashboard data from current player snapshots; v2 can add daily snapshots and event logs for true trends.

## Non-Goals

- Do not require Node at plugin runtime.
- Do not redesign core gameplay rules as part of this UI work.
- Do not move the Python package to a `src/` layout.
- Do not rewrite all admin APIs into a new backend architecture during v1.
- Do not expose raw JSON as the default editing experience for normal player-record fields.

## Architecture

### Front End

`webui/` will contain the React application:

- Vite app entry and build config.
- Tailwind theme matching a shadcn-like admin console.
- Local UI primitives for Button, Input, Select, Card, Table, Tabs, Dialog/Sheet, Badge, Alert, Skeleton, and Toast.
- Page modules for Dashboard, Players, Items, Beast Realm Cards, Equipment Rules, Mystic Drops, and Advanced Config.
- API client that reads the admin token from `localStorage` and sends `X-Xiuxian-Token`.

The front end should avoid CDN dependencies. Build output should be static files suitable for Starlette or the fallback HTTP server to serve directly.

### Runtime Static Assets

The production build should output to this package data directory:

```text
assets/admin_web/
```

`pyproject.toml` should include these built files in `tool.setuptools.package-data`. Runtime code should serve `index.html`, JS, CSS, and built assets from that directory. If the build output is missing in a development checkout, the admin route should return a readable setup hint instead of a blank page.

### Python Admin Server

`admin.py` remains responsible for:

- Auth checks using the existing token behavior.
- Existing JSON APIs.
- New dashboard aggregation API.
- Static file serving for the React build.
- Existing asset routes for item icons, portraits, and beast spell icons.
- Fallback built-in HTTP server behavior when Starlette integration is unavailable.

The current embedded `ADMIN_HTML` should be removed or reduced to a minimal fallback message once the React build is served.

## API Design

### Existing APIs

The React app should reuse these existing endpoints:

- `GET /api/config`
- `PUT /api/config`
- `GET /api/players`
- `GET /api/players/{user_id}`
- `PUT /api/players/{user_id}`
- `POST /api/backup`
- `GET /api/items`
- `GET /api/beast-realm/cards`
- `GET /api/equipment-rules`
- `GET /api/mystic`
- existing runtime asset routes

Request and response shapes should stay compatible unless a bug fix requires a narrow change.

### New Dashboard Endpoint

Add:

```text
GET /api/dashboard
```

The response should be derived from current player snapshots and contain:

- total player count
- today signed-in count
- recent active count
- inactive/risk count based on last sign date
- total and average spirit stones
- average and top battle power
- realm distribution
- recent sign-in list
- inactive player list
- quick health/risk flags
- version/capability metadata that makes room for future trend data

The endpoint should use the configured plugin timezone, matching the sign-in system.

### Future Stats Hooks

The v1 API should leave a clean extension point for future stats, for example:

```text
GET /api/stats/overview
GET /api/stats/activity
```

These endpoints are not required for v1 implementation. The v1 dashboard should gracefully label historical trend panels as snapshot-based when true history is unavailable.

## Layout And Navigation

The new admin console uses:

- fixed left sidebar for primary navigation
- top toolbar for token/login state, backup action, refresh, and status
- main content region with responsive width constraints
- compact cards and tables designed for repeated operational use
- no marketing/landing page layer

Navigation groups:

- Overview: Dashboard
- Management: Players, Items, Beast Realm Cards
- Rules: Equipment Rules, Mystic Drops
- Advanced: Raw Config

On narrow screens, the sidebar collapses to a sheet or compact rail, and data-heavy panels use horizontal scrolling rather than overflowing their containers.

## Page Designs

### Dashboard

The dashboard is the default page and focuses on player activity and retention.

First viewport:

- metric cards for total players, today's sign-ins, recent active players, inactive/risk players, average battle power, and total/average spirit stones
- compact status strip for data freshness and snapshot mode
- realm distribution chart
- battle power top list
- recent sign-ins and inactive players
- quick action tiles for Players, Mystic Drops, Equipment Rules, Beast Realm Cards, and Backup

The dashboard should favor clear operational signals over decorative visuals.

### Player Records

Players page:

- searchable/filterable player list
- player summary header with nickname/id, realm, battle power, stones, sign state, and risk hint
- structured form editor for all supported record fields
- object/list editors for roots, rewards, equipped artifacts, mystic state, daily tasks, and generic maps
- add/remove controls for repeatable sections
- fixed enumerations rendered as selects
- advanced unknown structures rendered through a generic editable object/list UI, not raw JSON by default

Raw JSON should be available only as an advanced escape hatch if needed.

### Item Catalog

Item page:

- searchable list with category, tier, quality, and customized filters
- table or dense card list view
- detail editor for category, possible tiers, possible grades, required realm, required attribute, usage, source, story, and parameter note
- visible customized/default state
- actions to save, reset unsaved changes, and restore default override

### Beast Realm Cards

Beast realm cards page:

- summary metrics for card count, follower/spell split, factions, and global pool count
- filters for search, kind, faction, realm/tier, and customized state
- list entries showing portrait/icon, name, kind, faction, cost, attack/defense, and pool copies
- detail form for card fields and copy count
- rules JSON kept in an advanced section because card rules are inherently structured and may remain expert-facing

### Equipment Rules

Equipment rules page:

- grouped editor by realm
- rows for min tier, max tier, grade, attribute, artifact name, and weight
- select controls for fixed values
- add/delete row actions
- advanced section for power bases, multipliers, or raw rule details that are not part of the common workflow

### Mystic Drops

Mystic drops page:

- top controls for mystic fishing option probability and sign-in extra fishing probability
- checkbox grids for normal and high-risk mystic types
- grouped category weight tables
- grouped fixed drop tables
- select controls for category, tier, grade, and item name
- add/delete row actions
- advanced raw mystic config section

The 5% mystic fishing option and 10% sign-in extra fishing chance should be visibly editable numeric inputs.

### Advanced Config

Raw config page:

- full `admin_config.json` editor
- parse validation before save
- explicit advanced warning
- save, refresh, and backup affordances

This page exists for power users and recovery, not as the primary management surface.

## Visual Design

The style target is shadcn-like:

- white and neutral surfaces
- subtle border hierarchy
- 8px or smaller radius for cards and controls
- restrained accent color usage
- dense but legible tables
- clear typography scale
- visible focus states
- simple empty/loading/error states

Avoid large decorative hero sections, gradient-orb backgrounds, oversized cards inside cards, and single-hue visual monotony. The UI should feel like an operational admin console rather than a landing page.

## State And Data Flow

The React app should centralize HTTP access in an API client:

- token loaded from `localStorage`
- token changes update future requests
- non-2xx responses become typed UI errors
- JSON parse failures are reported without losing user input

Pages own their form state. Save actions convert the form model back to the current backend JSON structures. After save, pages should reload the saved resource or reconcile returned data so the UI reflects backend-normalized values.

For editing pages, track dirty state and warn before discarding unsaved changes through navigation, refresh, or selecting another record.

## Error Handling

Required behavior:

- missing/invalid token shows a clear auth state
- failed list/detail loads show retry controls
- empty datasets show useful empty states
- save failures keep user edits visible
- JSON validation errors identify the parse problem
- missing built assets return a readable backend message
- dashboard trend areas explain when data is snapshot-based rather than historical

## Testing And Verification

Python checks:

- `python -m compileall .`
- focused tests or lightweight checks for dashboard aggregation, especially date handling and empty player data

Front-end checks:

- `npm run build`
- type check and lint if configured
- render checks for loading, empty, error, and normal states on core pages

Manual/browser checks:

- Dashboard renders with snapshot metrics
- Player search, detail load, structured edit, add/remove list item, and save work
- Item override save/reset/restore work
- Beast card save/reset/restore and icon/portrait rendering work
- Equipment row add/delete/save work
- Mystic probabilities, enabled type toggles, category rows, fixed drops, and save work
- Raw config parse failure and successful save work
- token save/auth failure flows are understandable
- narrow viewport does not produce text or controls outside their containers

## Rollout

Implementation should land in phases inside one feature branch:

1. Add React app structure, build tooling, and static serving path.
2. Add dashboard aggregation endpoint and dashboard page.
3. Port players page with structured editors.
4. Port items, beast realm cards, equipment rules, mystic drops, and advanced config.
5. Build static assets into the package runtime directory.
6. Verify package data and development docs.

Existing uncommitted gameplay/source changes should not be reverted or overwritten unless they directly conflict with the admin UI work.

## Implementation Notes

- The static output path is `assets/admin_web/` because it fits existing runtime asset conventions.
- If a field does not have known metadata, the UI should fall back to a generic text/number/object/list editor rather than blocking edits.
- Historical charts are not required in v1, but components and API response shapes should make future trend data easy to add.

