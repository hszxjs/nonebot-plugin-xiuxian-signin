# Ant Design WebUI Redesign Design

Date: 2026-07-10

## Goal

Rebuild the existing admin WebUI with Ant Design while preserving current content data, API behavior, asset usage, and editing workflows. The current HTML structure, local UI primitives, Tailwind-oriented visual styling, and page layout decisions are not constraints for the redesign.

The new UI should prioritize rule configuration clarity and daily operation efficiency:

- Rule-heavy areas must be easier to scan, navigate, and edit.
- Daily tasks such as checking player status, locating records, and editing one object should remain fast.
- Ant Design's component system should provide the visual styling, interaction states, validation states, and layout primitives.

## Current Content Inventory

The current frontend contains these primary pages and data sources:

- Dashboard: `/api/dashboard`
  - Metrics: total players, today's sign-ins, recent active players, inactive-risk players, average battle power, total spirit stones.
  - Chart: realm distribution vertical bar chart.
  - Lists: top battle power, recent sign-ins, inactive players.
- Players: `/api/players`, `/api/players/{user_id}`
  - Player list: player, realm, battle power, spirit stones.
  - Detail groups: base state, dates, roots and breakthrough, equipment and growth, identity and tasks, mystic and boss state, rewards and immortal seeds, other fields.
- Items: `/api/items`, `/api/config`
  - Item list with icon, category, tiers, grades, required realm, required attribute, customized state.
  - Detail fields: category, required realm, required root, tiers, grades, usage, source, story, parameter note.
- Beast cards: `/api/beast-realm/cards`, `/api/config`
  - Card list with portrait or spell icon, kind, faction/category, cost, attack, defense, pool copies, customized state.
  - Detail fields: name, realm, faction, cost, attack, defense, pool copies, tier, element, category, target, portrait ID, icon ID, source realm, archetype, effect, story, rules JSON.
- Equipment rules: `/api/equipment-rules`, `/api/config`
  - Realm-grouped drop rules.
  - Rule fields: min tier, max tier, grade, root attribute, artifact name, weight.
- Mystic drops: `/api/mystic`, `/api/items`, `/api/config`
  - Probability fields: mystic fishing option rate, sign-in extra fishing chance rate.
  - Enabled normal and high-risk mystic types.
  - Per-type category weights and fixed drop pools.
  - Drop fields: category, tier, grade, item name, weight.
- Advanced config: `/api/config`, `/api/equipment-rules`
  - Global parameters, equipment power model, page-managed config summary, raw config escape hatch.

Image assets must continue to use existing authenticated asset routes:

- Item icons: `/assets/item-icons/...`
- Character portraits: `/assets/character-portraits/...`
- Beast spell icons: `/assets/beast-spell-icons/...`

## Approved UI Direction

Use a domain navigation plus detail-drawer model.

Rejected alternatives:

- Deep subpages for every rule subsection: clearer in isolation, but too many route hops for daily edits.
- Flat pages with all content visible: simpler implementation, but too dense for players, mystic drops, equipment rules, and advanced config.

Approved approach:

- Keep top-level navigation small.
- Split high-density areas with tabs, segmented controls, or local subnavigation.
- Keep object lists on the main page.
- Put single-object editing in drawers.
- Put high-risk confirmations in modals or popconfirms.
- Put low-frequency expert fields in collapsible advanced sections.

## Navigation

Top-level navigation:

1. Dashboard
2. Players
3. Items
4. Beast Cards
5. Rules
6. System Config

Rules contains:

- Equipment Drops
- Mystic Drops

System Config contains:

- Global Parameters
- Equipment Power Model
- Config Overview
- Raw Config

Equipment rules and mystic drops are grouped under Rules because both are rule-maintenance workflows. Global settings and raw configuration are grouped under System Config because they are cross-cutting administrative settings rather than gameplay rule tables.

## Page Designs

### Dashboard

Dashboard remains a single page.

Content:

- Statistic cards for total players, today sign-ins, recent active players, inactive-risk players, average battle power, total spirit stones.
- Realm distribution chart.
- Battle power ranking.
- Recent sign-in list.
- Inactive-risk player list.
- Snapshot date and snapshot-mode indicator.

Ant Design components:

- `Card`
- `Statistic`
- `Row` / `Col` or `Flex`
- `Table` or `List`
- `Tag`
- `Alert` for snapshot-mode notes when useful.

Charting:

- Keep Recharts initially to avoid a new chart dependency.
- `@ant-design/charts` can be considered only after explicit dependency approval.

### Players

Players uses a table-first layout.

Main page:

- Search by player ID or nickname.
- Player table with player, realm, battle power, spirit stones.
- Loading, empty, error, and retry states.

Detail drawer:

- Opens when selecting a player.
- Uses `Tabs` to group the existing player sections:
  - Base State
  - Dates
  - Roots and Breakthrough
  - Equipment and Growth
  - Identity and Tasks
  - Mystic and Boss
  - Rewards and Immortal Seeds
  - Other Fields
- Uses `Form`, `Input`, `InputNumber`, `Select`, `Switch`, `DatePicker` where applicable.
- Uses generic object/list editors only for fields without stronger metadata.

Save behavior:

- Drawer footer contains Save, Reload, and dirty-state indication.
- Unsaved changes block player switching unless confirmed.

### Items

Items uses list/table plus drawer editing.

Main page:

- Search by item name, usage, source.
- Filters for category and tier.
- Show item icon, category, tiers, grades, required realm/root, customized state.

Detail drawer:

- Basic fields: category, required realm, required root.
- Repeatable fields: tiers, grades.
- Text fields: usage, source, story.
- Parameter note is read-only unless future backend semantics require editing.
- Restore default remains available for customized records.

### Beast Cards

Beast Cards uses list/table plus drawer editing.

Main page:

- Search by card name, ID, effect.
- Filters for kind, faction, and optionally realm/category.
- Show portrait or spell icon, kind, faction/category, cost, attack, defense, pool copies, customized state.

Detail drawer:

- Basic fields: name, realm, faction, cost, attack, defense, pool copies.
- Structure fields: tier, element, category, target, portrait ID, icon ID, source realm, archetype.
- Text fields: effect, story.
- Advanced collapse: rules JSON.

Rules JSON remains an advanced field because it is structured and expert-facing.

### Rules: Equipment Drops

Equipment Drops should not render every realm as a long flat page.

Layout:

- Top-level rules page uses `Tabs` or local navigation.
- Equipment Drops view groups by realm.
- Realm selection uses either `Tabs` for a moderate number of realms or a searchable side list for many realms.

Editor:

- Editable table or `Form.List` rows.
- Fields: min tier, max tier, grade, root attribute, artifact name, weight.
- Add/delete rows with `Button` and `Popconfirm` for destructive actions when needed.

### Rules: Mystic Drops

Mystic Drops splits probability settings from per-type drop editing.

Sections:

- Probability settings: mystic fishing option rate and sign-in extra fishing chance rate.
- Enabled types: normal mystic types and high-risk mystic types.
- Per-type drop configuration.

Per-type editor:

- Category weights table.
- Fixed drops table.
- Fields: category, tier, grade, item name, weight.
- Type selection uses tabs or a searchable list depending on type count.

### System Config

System Config contains cross-cutting and expert-facing configuration.

Subsections:

- Global Parameters:
  - Config version.
  - Beast default pool copies.
  - Artifact immortal upgrade rate.
  - Mystic fishing option rate.
  - Sign-in extra fishing probability.
- Equipment Power Model:
  - Tier default realm.
  - Realm tier unlocks.
  - Artifact category power base.
  - Artifact realm power base.
  - Artifact tier power ratio.
  - Artifact grade ratio.
- Config Overview:
  - Item overrides.
  - Beast card overrides.
  - Equipment drop pools.
  - Mystic category weights.
  - Mystic fixed drops.
  - Unknown extra keys.
- Raw Config:
  - Advanced JSON editor.
  - Parse validation before save.
  - Clear warning that this is an expert fallback.

## Interaction Placement

Use `Drawer` for single-object detail editing:

- Player detail.
- Item detail.
- Beast card detail.

Use `Modal`, `Popconfirm`, or `Result` for short confirmation and result flows:

- Unsaved navigation.
- Restore default.
- Delete row.
- Save failure retry context.
- Backup result.

Use `Collapse` or an advanced tab for low-frequency expert content:

- Rules JSON.
- Raw config.
- Unknown fields.
- Debug-like metadata.

Use `Tabs` or `Segmented` for same-page business grouping:

- Player detail field groups.
- Rules subviews.
- Mystic type groups.
- System config sections.

## Ant Design Usage Constraints

Prefer Ant Design component APIs over external style overrides:

- Theme tokens are set through `ConfigProvider`.
- Component variants, statuses, sizes, and layout props are preferred for visual state.
- `className` is limited to page-level layout, spacing, width, and alignment.
- Do not replace Ant Design button, form, table, input, select, modal, drawer, or validation behavior with custom CSS.
- Avoid hand-written CSS for component colors, typography, borders, hover states, and internal control behavior.

The UI should stay operational and dense:

- No landing page.
- No hero layout.
- No decorative gradient/orb background.
- No nested cards.
- No large marketing-style cards.
- Use 8px or smaller card/control radii unless Ant Design token defaults dictate otherwise.

## State And Data Flow

Preserve the existing API client model:

- Token is loaded from URL or local storage.
- Requests include `X-Xiuxian-Token`.
- API errors become visible UI errors.
- JSON parse failures are reported without losing user input.

Editing pages own their draft state:

- Draft state is initialized from loaded backend data.
- Dirty state is tracked per editable surface.
- Save converts the draft back to existing backend JSON shapes.
- After save, reload or reconcile returned data so the UI reflects backend-normalized values.

## Error Handling

Required behaviors:

- Missing or invalid token shows a clear auth state.
- Loading states are visible for every page and drawer.
- Empty states explain what data is missing.
- Failed loads show retry controls.
- Save failures preserve unsaved edits.
- JSON parse failures identify the parse problem.
- Missing image assets fall back to an icon placeholder without breaking layout.
- Snapshot-only dashboard data is labeled accurately.

## Dependency Decisions

Ant Design is a new dependency and requires explicit approval before implementation changes:

- Required: `antd`
- Optional: `@ant-design/icons` if icon coverage is needed beyond current `lucide-react`
- Optional: `@ant-design/charts` only if replacing Recharts is approved

Default implementation should minimize dependency churn:

- Add `antd`.
- Keep Recharts unless the user approves chart migration.
- Remove local UI primitives only after Ant Design replacements are in place.

## Verification Plan

Frontend verification:

- Run the configured frontend type/build command with `pnpm`.
- Verify desktop and narrow viewport layouts.
- Check table overflow, drawer width, form label wrapping, and long Chinese text.
- Check item icons, beast portraits, and spell icons.
- Check loading, empty, error, dirty, save success, and save failure states.

Python/backend verification:

- Run affected tests if API/static serving/package data changes are made.
- If backend is not changed, state that backend tests were not required for the UI-only change.

Manual checks:

- Dashboard renders metrics and chart.
- Player list and detail drawer work.
- Item detail edit and restore default work.
- Beast card detail edit and rules JSON validation work.
- Equipment rule row add/delete/save works.
- Mystic probabilities, type enablement, weights, and fixed drops work.
- Raw config validation blocks invalid JSON.
- Narrow viewport does not produce overlapping or clipped controls.

## Open Implementation Decisions

These must be resolved before code changes:

- Whether to add only `antd`, or also add `@ant-design/icons`.
- Whether to keep Recharts or migrate charts to `@ant-design/charts`.
- Whether Rules and System Config use URL-level subroutes or in-page tabs. The recommended default is in-page tabs unless route persistence is explicitly desired.
- Whether to remove Tailwind immediately or leave it temporarily for page-level layout during migration. The recommended default is to remove visual dependency on Tailwind, while allowing minimal layout classes only during transition if removal would increase risk.
