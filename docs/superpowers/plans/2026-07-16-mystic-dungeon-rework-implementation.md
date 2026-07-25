# Mystic Dungeon Rework Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the legacy ten-exploration mystic realm with persistent 24–48 node single-player and 2–3 player team dungeons, private-chat PVE encounters, segmented team Boss battles, map rendering, and editable Web configuration.

**Architecture:** Store each dungeon as a shared `MysticDungeonRun` aggregate in a dedicated JSON store and keep only an active-run index plus idempotent settlement keys on player records. Put deterministic map and movement rules in `mystic_dungeon.py`, incremental PVE coordination in `mystic_battle.py`, Pillow rendering in `mystic_cards.py`, and command/storage orchestration in `mystic_runtime.py`; keep `__init__.py` as a thin NoneBot transport layer. Reuse existing combat calculations by extracting a stateful single-action resolver from `domain.py` without changing normal PVP behavior.

**Tech Stack:** Python 3.12+, NoneBot2, asyncio, dataclasses/enums, JSON persistence with temp-file replacement, Pillow, FastAPI, Pydantic, React 19, TypeScript 6, Ant Design 6, SWR, Vitest, uv, ruff, mypy, pnpm, Biome.

---

## Execution Constraints

- Do not modify runtime code until the user explicitly approves this plan.
- Do not create commits unless the user explicitly requests them. Commit steps are intentionally omitted despite the generic skill template.
- Do not run formatters unless the user explicitly requests formatting. `ruff check` and `biome check` are required; write mode is not.
- Before Task 1 changes dependencies, obtain explicit approval for `mypy` and `@biomejs/biome`, and for removing ESLint/Prettier packages.
- Preserve unrelated dirty-worktree changes. Inspect `git diff` before every task that touches an already modified file.
- Do not add a database, Redis, or another runtime dependency.

## Phase Boundaries

1. Tasks 1–7 produce a tested persistent dungeon core with no public bot entry.
2. Tasks 8–12 expose group/private gameplay and restart recovery.
3. Tasks 13–16 add rendering, generated assets, Web configuration, cleanup, and final verification.

## File Structure

Create:

- `mystic_dungeon.py` - map catalog, run aggregate, movement, node content, votes, and reward ledgers.
- `mystic_battle.py` - incremental PVE state, shared encounters, Boss segments, AI turns, and rescue coordination.
- `mystic_cards.py` - full-map Pillow renderer and text fallback.
- `mystic_runtime.py` - command parsing, store/service orchestration, deadlines, and transport-neutral results.
- `tests/test_combat_turns.py` - extracted combat-action resolver regression tests.
- `tests/test_mystic_dungeon.py` - map, movement, team, vote, node, and reward tests.
- `tests/test_mystic_storage.py` - JSON persistence, recovery, and idempotent settlement tests.
- `tests/test_mystic_battle.py` - ordinary encounter, Boss segment, auto-battle, and rescue tests.
- `tests/test_mystic_cards.py` - map crop, icon, color-state, and pixel-coverage tests.
- `tests/test_mystic_integration.py` - service-level group/private flow and restart tests without importing a live adapter.
- `tools/render_mystic_map_preview.py` - deterministic 24/48 node preview generator.
- `tools/generate_mystic_map_backgrounds_gpt.py` - `gpt-image-2` prompt generation and source-image processing.
- `assets/mystic_maps/manifest.json` - 26 theme ids, display names, risk classes, template ids, and background paths.
- `assets/mystic_maps/templates.json` - normalized node and edge templates for all 26 themes.
- `assets/mystic_maps/backgrounds/*.png` - 26 published 3840x2160 background plates.
- `assets/mystic_dungeon_ui/boss_label.png` - published transparent BOSS lightning label.
- `webui/biome.json` - Biome lint/format configuration.
- `webui/src/features/mystic/mystic-workspace.test.tsx` - editable mystic configuration tests.

Modify:

- `pyproject.toml` - Python 3.12 metadata, mypy dev dependency/config, package-data paths.
- `domain.py` - stateful combat-action primitive; remove legacy mystic state fields and ten-exploration functions.
- `storage.py` - persistent run store, active user index, rescue state, and idempotent entry/reward settlement.
- `__init__.py` - replace legacy entrance/explore handlers with group/private dungeon handlers and recovery scheduling.
- `admin.py` - validated mystic config schema, payload, `PUT /api/mystic`, and new module config application.
- `tests/test_domain_features.py` - remove legacy exploration tests and retain non-mystic regression coverage.
- `tests/test_admin_routes.py` - configuration validation and API route tests.
- `cards.py` - only export/reuse shared rendering helpers if `mystic_cards.py` cannot import an existing public helper.
- `webui/package.json` and `webui/pnpm-lock.yaml` - replace ESLint/Prettier tooling with Biome.
- `webui/src/lib/types.ts` - structured mystic config types.
- `webui/src/lib/api.ts` and `webui/src/lib/api.test.ts` - `saveMysticConfig` request.
- `webui/src/features/mystic/mystic-workspace.tsx` - editable map, probability, combat, timeout, and asset controls.
- `webui/src/App.tsx` - save/mutate wiring for the mystic page.

Delete:

- `webui/eslint.config.js` - forbidden by repository instructions once Biome is approved.

Published background filenames:

- `ancient_sect_ruins.png`, `beast_tide.png`, `ancient_cultivator_cave.png`, `star_mine.png`, `soul_remnant.png`, `bronze_cloud_palace.png`.
- `far_wilderness_boundary.png`, `silent_black_mountain.png`, `prime_star_mine.png`, `fallen_god_ruins.png`, `immortal_sleep_valley.png`, `reincarnation_tide_eye.png`, `burial_sky_island.png`, `qiongheng_ancient_hall.png`, `five_elements_land.png`, `outer_battlefield.png`, `nether_spring_demon_sect.png`, `dust_ruins.png`, `star_fate_lonely_realm.png`, `heaven_gate_battlefield.png`, `seven_constellations_road.png`, `bronze_cloud_deep.png`, `thunder_pool.png`, `mystic_stone_gate.png`, `starfall_remnant.png`, `green_mystic_shadow.png`.

---

### Task 1: Toolchain Approval And Metadata Alignment

**Files:**
- Modify: `pyproject.toml`
- Modify: `webui/package.json`
- Modify: `webui/pnpm-lock.yaml`
- Create: `webui/biome.json`
- Delete: `webui/eslint.config.js`

- [ ] **Step 1: Request dependency approval**

Ask the user to approve exactly these development-tool changes before running an install command:

```text
Add Python dev dependency: mypy>=1.11
Add frontend dev dependency: @biomejs/biome>=2.0
Remove frontend dev dependencies: @eslint/js, eslint, eslint-plugin-react-hooks,
eslint-plugin-react-refresh, globals, prettier, typescript-eslint
Raise package metadata from Python >=3.10 to Python >=3.12
```

Expected: explicit approval. Stop Task 1 if approval is not granted.

- [ ] **Step 2: Write the metadata changes**

Update the relevant `pyproject.toml` sections to:

```toml
[project]
requires-python = ">=3.12, <4.0"

[project.optional-dependencies]
dev = [
    "mypy>=1.11",
    "ruff>=0.4.0",
]

[tool.ruff]
line-length = 120
target-version = "py312"

[tool.mypy]
python_version = "3.12"
files = [
    "mystic_dungeon.py",
    "mystic_battle.py",
    "mystic_cards.py",
    "mystic_runtime.py",
    "storage.py",
    "admin.py",
]
check_untyped_defs = true
no_implicit_optional = true
warn_unused_ignores = true
```

Update `webui/package.json` scripts and dev dependencies:

```json
{
  "scripts": {
    "dev": "vite",
    "build": "tsc -b && vite build",
    "lint": "biome check .",
    "test": "vitest run",
    "typecheck": "tsc --noEmit",
    "preview": "vite preview"
  },
  "devDependencies": {
    "@biomejs/biome": "^2.0.0",
    "@testing-library/jest-dom": "^6.9.1",
    "@testing-library/react": "^16.3.2",
    "@types/node": "^24",
    "@types/react": "^19",
    "@types/react-dom": "^19",
    "@vitejs/plugin-react": "^6",
    "jsdom": "^29.1.1",
    "typescript": "~6",
    "vite": "^8",
    "vitest": "^4.1.10"
  }
}
```

Create `webui/biome.json`:

```json
{
  "$schema": "https://biomejs.dev/schemas/2.0.0/schema.json",
  "files": { "includes": ["src/**/*.ts", "src/**/*.tsx", "vite.config.ts"] },
  "formatter": { "enabled": true, "indentStyle": "space", "indentWidth": 2 },
  "linter": { "enabled": true, "rules": { "recommended": true } },
  "javascript": { "formatter": { "quoteStyle": "double", "semicolons": "asNeeded" } }
}
```

- [ ] **Step 3: Refresh lockfiles without formatting source**

Run:

```powershell
uv sync --extra dev
Set-Location webui
pnpm install
Set-Location ..
```

Expected: both commands complete successfully and only dependency metadata/lockfiles change.

- [ ] **Step 4: Verify tool availability**

Run:

```powershell
uv run python --version
uv run mypy --version
Set-Location webui
pnpm exec biome --version
Set-Location ..
```

Expected: Python reports 3.12 or newer; mypy and Biome print versions.

---

### Task 2: Extract A Stateful Combat Action Primitive

**Files:**
- Create: `tests/test_combat_turns.py`
- Modify: `domain.py:6131-6480`

- [ ] **Step 1: Write failing state-carrying combat tests**

Create `tests/test_combat_turns.py` with a local loader matching `tests/test_domain_features.py` and these tests:

```python
def test_combat_runtime_state_tracks_hp_mana_and_cooldowns() -> None:
    record = combat_record("42")
    state = domain.CombatRuntimeState.initial(record)

    first = domain.resolve_combat_action(record, "普通攻击", state, "turn:1")
    second = domain.resolve_combat_action(record, "普通攻击", first.state, "turn:2")

    assert first.damage > 0
    assert second.state.turn == 2
    assert second.state.hp == first.state.hp
    assert second.state.mana <= first.state.mana


def test_existing_action_evaluator_folds_the_single_action_resolver() -> None:
    record = combat_record("42")
    actions = [{"text": "普通攻击"}, {"text": "普通攻击"}]

    aggregate = domain.evaluate_combat_actions(record, actions, "regression")
    state = domain.CombatRuntimeState.initial(record)
    outcomes = []
    for index, action in enumerate(actions):
        outcome = domain.resolve_combat_action(record, action["text"], state, f"regression:{index}")
        outcomes.append(outcome)
        state = outcome.state

    assert aggregate["damage"] == sum(item.damage for item in outcomes)
    assert aggregate["mana"] == state.mana
    assert aggregate["cooldowns"] == state.cooldowns
```

`combat_record()` must create a deterministic `UserRecord` with a valid root and combat profile, without relying on the old mystic state.

- [ ] **Step 2: Run the tests and confirm the API is missing**

Run:

```powershell
uv run pytest tests/test_combat_turns.py -q
```

Expected: FAIL because `CombatRuntimeState` and `resolve_combat_action` do not exist.

- [ ] **Step 3: Add immutable action state and result types**

Add near the current combat helpers in `domain.py`:

```python
@dataclass(frozen=True)
class CombatRuntimeState:
    hp: int
    max_hp: int
    mana: int
    max_mana: int
    cooldowns: dict[str, int]
    turn: int = 0

    @classmethod
    def initial(cls, record: UserRecord) -> "CombatRuntimeState":
        return cls(
            hp=combat_max_hp(record),
            max_hp=combat_max_hp(record),
            mana=combat_max_mana(record),
            max_mana=combat_max_mana(record),
            cooldowns={},
        )


@dataclass(frozen=True)
class CombatActionOutcome:
    state: CombatRuntimeState
    damage: int
    defense: int
    speed: int
    triggered: tuple[str, ...]
    logs: tuple[str, ...]
```

- [ ] **Step 4: Extract the existing per-action loop body**

Create this public function and move the current single-action logic from `evaluate_combat_actions()` into it without changing damage, talisman, technique, trait, mana, or cooldown formulas:

```python
def resolve_combat_action(
    record: UserRecord,
    action_text: str,
    state: CombatRuntimeState,
    seed: str,
) -> CombatActionOutcome:
    next_cooldowns = {name: max(0, value - 1) for name, value in state.cooldowns.items() if value > 1}
    result = _evaluate_one_combat_action(
        record=record,
        action_text=action_text,
        mana=state.mana,
        cooldowns=next_cooldowns,
        seed=seed,
    )
    next_state = CombatRuntimeState(
        hp=state.hp,
        max_hp=state.max_hp,
        mana=max(0, int(result["mana"])),
        max_mana=state.max_mana,
        cooldowns={str(key): int(value) for key, value in dict(result["cooldowns"]).items()},
        turn=state.turn + 1,
    )
    return CombatActionOutcome(
        state=next_state,
        damage=max(1, int(result["damage"])),
        defense=max(0, int(result["defense"])),
        speed=int(result["speed"]),
        triggered=tuple(str(item) for item in result["triggered"]),
        logs=tuple(str(item) for item in result["logs"]),
    )
```

`_evaluate_one_combat_action()` is the extracted current loop body and must catch only the specific conversion or lookup exceptions already handled by the old code; do not add a bare `except`.

- [ ] **Step 5: Rebuild the old aggregate evaluator on the new primitive**

Rewrite `evaluate_combat_actions()` to initialize `CombatRuntimeState`, call `resolve_combat_action()` for each action, and aggregate the returned fields. Keep its existing dictionary keys so `simulate_normal_duel()` and current cards remain compatible.

- [ ] **Step 6: Run focused and existing combat tests**

Run:

```powershell
uv run pytest tests/test_combat_turns.py tests/test_domain_features.py -q
```

Expected: PASS with no change to existing normal duel behavior.

---

### Task 3: Add Fixed Map Catalog And Validation

**Files:**
- Create: `mystic_dungeon.py`
- Create: `assets/mystic_maps/manifest.json`
- Create: `assets/mystic_maps/templates.json`
- Create: `tests/test_mystic_dungeon.py`

- [ ] **Step 1: Write failing catalog and tier tests**

Add tests:

```python
def test_map_size_uses_supported_realm_tiers() -> None:
    expected = {0: 24, 5: 28, 10: 32, 15: 36, 20: 40, 25: 44, 30: 48}
    for realm_index, node_count in expected.items():
        assert map_size_for_boss(realm_index, DEFAULT_MAP_SIZE_RULES) == node_count


def test_every_template_is_connected_for_every_active_size(catalog: MysticTemplateCatalog) -> None:
    for template in catalog.templates.values():
        for size in SUPPORTED_MAP_SIZES:
            active = template.active_graph(size)
            assert len(active.nodes) == size
            assert active.has_path(active.start_node_id, active.boss_node_id)


def test_high_risk_loops_never_form_the_only_boss_route(catalog: MysticTemplateCatalog) -> None:
    for template in catalog.high_risk_templates():
        template.validate_loop_safety()
```

- [ ] **Step 2: Run the tests and confirm imports fail**

Run:

```powershell
uv run pytest tests/test_mystic_dungeon.py -q
```

Expected: FAIL because `mystic_dungeon.py` and the resource files do not exist.

- [ ] **Step 3: Define exact map types**

Create `mystic_dungeon.py` with:

```python
from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from typing import Any


SUPPORTED_MAP_SIZES = (24, 28, 32, 36, 40, 44, 48)
DEFAULT_MAP_SIZE_RULES = ((0, 24), (5, 28), (10, 32), (15, 36), (20, 40), (25, 44), (30, 48))


class DungeonRisk(StrEnum):
    NORMAL = "normal"
    HIGH = "high"


class NodeKind(StrEnum):
    START = "start"
    RANDOM = "random"
    COMBAT = "combat"
    RESOURCE = "resource"
    TRAP = "trap"
    REST = "rest"
    BOSS = "boss"


@dataclass(frozen=True)
class DungeonNodeSlot:
    node_id: str
    x: float
    y: float
    depth: int
    activation_size: int
    allowed_kinds: tuple[NodeKind, ...]
    is_safe: bool = False
    is_terminal_candidate: bool = False


@dataclass(frozen=True)
class DungeonEdge:
    edge_id: str
    source_node_id: str
    target_node_id: str
    activation_size: int
    is_loop: bool = False
```

Add `DungeonMapTemplate`, `ActiveDungeonGraph`, `MysticThemeDefinition`, and `MysticTemplateCatalog` with `from_files()`, `active_graph()`, connectivity validation, branch counts, and loop-safety validation.

- [ ] **Step 4: Implement deterministic size selection**

```python
def map_size_for_boss(realm_index: int, rules: tuple[tuple[int, int], ...]) -> int:
    selected = SUPPORTED_MAP_SIZES[0]
    for minimum_realm, node_count in sorted(rules):
        if realm_index < minimum_realm:
            break
        selected = node_count
    if selected not in SUPPORTED_MAP_SIZES:
        raise ValueError(f"unsupported map size: {selected}")
    return selected
```

- [ ] **Step 5: Create the manifest and 48-node templates**

`manifest.json` must contain all 26 display names and exact published background filenames. `templates.json` must contain one normalized 48-node graph per theme with `activation_size` values that produce exactly the seven supported sizes.

Use this top-level structure:

```json
{
  "schema_version": 1,
  "themes": {
    "ancient_sect_ruins": {
      "display_name": "上古宗门遗址",
      "risk": "normal",
      "template_id": "ancient_sect_ruins",
      "background": "backgrounds/ancient_sect_ruins.png"
    }
  }
}
```

The template generator must place nodes irregularly, keep coordinates in `[0, 1]`, provide medium branching for normal themes, and dense branching plus limited loops for high-risk themes.

- [ ] **Step 6: Run catalog tests**

Run:

```powershell
uv run pytest tests/test_mystic_dungeon.py -q
```

Expected: PASS for node counts, connectivity, branch density, and loop safety.

---

### Task 4: Implement The Dungeon Aggregate And Movement Service

**Files:**
- Modify: `mystic_dungeon.py`
- Modify: `tests/test_mystic_dungeon.py`

- [ ] **Step 1: Write failing lobby and movement tests**

Add tests covering:

```python
def test_team_start_locks_two_or_three_members_and_charges_only_leader() -> None:
    run = service.create_lobby("run-1", "100", "leader", DungeonRisk.NORMAL)
    service.join_lobby(run, "member-2")
    service.set_ready(run, "leader", True)
    service.set_ready(run, "member-2", True)

    charge = service.start_run(run, boss_realm_index=4, map_seed=7, content_seed=11)

    assert run.phase is DungeonPhase.READY_TO_ROLL
    assert run.member_ids == ("leader", "member-2")
    assert charge.payer_id == "leader"
    assert charge.amount == 1


def test_solo_start_creates_one_member_run_and_charges_that_player() -> None:
    run, charge = service.create_solo_run(
        run_id="run-solo",
        group_id="100",
        user_id="solo",
        risk=DungeonRisk.NORMAL,
        boss_realm_index=4,
        map_seed=7,
        content_seed=11,
    )
    assert run.mode is DungeonMode.SOLO
    assert run.member_ids == ("solo",)
    assert charge.payer_id == "solo"


def test_roll_pauses_at_branch_and_resumes_remaining_steps() -> None:
    run = started_run_at_branch(service)
    movement = service.roll(run, actor_id=run.leader_id, dice_value=6)
    assert movement.pending_branch_choices
    assert run.remaining_steps > 0

    service.choose_branch(run, actor_id=run.leader_id, target_node_id=movement.pending_branch_choices[0])
    assert run.remaining_steps == 0


def test_boss_overshoot_stops_on_boss() -> None:
    run = run_one_edge_before_boss(service)
    service.roll(run, actor_id=run.leader_id, dice_value=6)
    assert run.current_node_id == run.boss_node_id
    assert run.remaining_steps == 0
```

Also cover wrong actor, revisit without duplicate resolution, movement blocked during combat, and member replacement after start.

- [ ] **Step 2: Run the tests and confirm service types are missing**

Run:

```powershell
uv run pytest tests/test_mystic_dungeon.py -q
```

Expected: FAIL on missing aggregate and service types.

- [ ] **Step 3: Add aggregate enums and dataclasses**

```python
class DungeonMode(StrEnum):
    SOLO = "solo"
    TEAM = "team"


class DungeonPhase(StrEnum):
    CREATING = "creating"
    LOBBY = "lobby"
    READY_TO_ROLL = "ready_to_roll"
    MOVING = "moving"
    AWAITING_BRANCH = "awaiting_branch"
    RESOLVING_NODE = "resolving_node"
    AWAITING_ENCOUNTER_RESPONSE = "awaiting_encounter_response"
    PREPARING_BATTLE = "preparing_battle"
    BATTLE_TURN = "battle_turn"
    AWAITING_RESCUE = "awaiting_rescue"
    AWAITING_BOSS_VOTE = "awaiting_boss_vote"
    AWAITING_LEADER_TRANSFER_VOTE = "awaiting_leader_transfer_vote"
    COMPLETED = "completed"
    FAILED = "failed"
    ABANDONED = "abandoned"


@dataclass
class MysticDungeonMember:
    user_id: str
    nickname: str
    ready: bool = False
    joined_at: str = ""
    boss_segment_id: str | None = None
    boss_segment_cleared: bool = False


@dataclass
class MysticDungeonRun:
    run_id: str
    source_group_id: str
    mode: DungeonMode
    risk: DungeonRisk
    leader_id: str
    members: dict[str, MysticDungeonMember]
    phase: DungeonPhase = DungeonPhase.LOBBY
    template_id: str = ""
    theme_id: str = ""
    map_size: int = 24
    map_seed: int = 0
    content_seed: int = 0
    current_node_id: str = ""
    boss_node_id: str = ""
    visited_node_ids: list[str] = field(default_factory=list)
    visited_edge_ids: list[str] = field(default_factory=list)
    cleared_node_ids: list[str] = field(default_factory=list)
    remaining_steps: int = 0
    pending_branch_choices: list[str] = field(default_factory=list)
    last_leader_action_at: str = ""
    active_encounter_id: str | None = None
    temporary_rewards_by_user: dict[str, list[dict[str, Any]]] = field(default_factory=dict)
    revision: int = 0


@dataclass(frozen=True)
class EntryCharge:
    payer_id: str
    token_name: str
    amount: int = 1


@dataclass(frozen=True)
class MovementResult:
    traversed_edge_ids: tuple[str, ...]
    landed_node_id: str | None
    pending_branch_choices: tuple[str, ...]
    node_resolution_required: bool


class VoteKind(StrEnum):
    BOSS_CONTINUE = "boss_continue"
    LEADER_TRANSFER = "leader_transfer"
    ABANDON = "abandon"


@dataclass
class DungeonVote:
    vote_id: str
    kind: VoteKind
    eligible_user_ids: tuple[str, ...]
    approvals: set[str]
    rejections: set[str]
    deadline: str


@dataclass(frozen=True)
class VoteResult:
    passed: bool
    failed: bool
    pending: bool
```

Implement explicit `to_dict()` and `from_dict()` methods; reject unknown phase or invalid roster sizes instead of silently accepting corrupt state.

- [ ] **Step 4: Implement `MysticDungeonService`**

The public surface must expose these exact signatures:

- `MysticDungeonService(catalog: MysticTemplateCatalog, now: Callable[[], datetime])`
- `create_solo_run(run_id: str, group_id: str, user_id: str, risk: DungeonRisk, boss_realm_index: int, map_seed: int, content_seed: int) -> tuple[MysticDungeonRun, EntryCharge]`
- `create_lobby(run_id: str, group_id: str, leader_id: str, risk: DungeonRisk) -> MysticDungeonRun`
- `join_lobby(run: MysticDungeonRun, user_id: str, nickname: str = "") -> None`
- `remove_lobby_member(run: MysticDungeonRun, user_id: str) -> None`
- `set_ready(run: MysticDungeonRun, user_id: str, ready: bool) -> None`
- `start_run(run: MysticDungeonRun, boss_realm_index: int, map_seed: int, content_seed: int) -> EntryCharge`
- `roll(run: MysticDungeonRun, actor_id: str, dice_value: int) -> MovementResult`
- `choose_branch(run: MysticDungeonRun, actor_id: str, target_node_id: str) -> MovementResult`
- `begin_leader_transfer(run: MysticDungeonRun, actor_id: str, nominee_id: str, deadline: datetime) -> DungeonVote`
- `cast_vote(run: MysticDungeonRun, actor_id: str, approve: bool) -> VoteResult`
- `begin_abandon_vote(run: MysticDungeonRun, actor_id: str, deadline: datetime) -> DungeonVote`

Use a shared `_advance(run, steps)` method. It must stop at a branch before consuming the outgoing edge, preserve remaining steps, stop at Boss, append traversed edges exactly once, and return the final landing node only when movement is complete.

- [ ] **Step 5: Run movement and vote tests**

Run:

```powershell
uv run pytest tests/test_mystic_dungeon.py -q
```

Expected: PASS for solo/team lobby, roster locking, dice movement, branch resume, Boss stop, revisits, transfer vote, and abandon vote.

---

### Task 5: Persist Runs And Idempotent Settlements

**Files:**
- Modify: `domain.py:2472-2800`
- Modify: `storage.py`
- Create: `tests/test_mystic_storage.py`

- [ ] **Step 1: Write failing persistence and settlement tests**

Create tests using `tempfile.TemporaryDirectory()` and `asyncio.run()`:

```python
def test_create_team_run_charges_only_leader_and_indexes_every_member() -> None:
    store, leader, member = prepared_store_with_tokens()
    run = team_run("run-1", leader.user_id, member.user_id)

    saved = asyncio.run(store.create_mystic_run(run, payer_id=leader.user_id, token_name="普通秘境令牌"))

    assert saved.phase == DungeonPhase.READY_TO_ROLL
    assert asyncio.run(store.find_active_mystic_run_id(leader.user_id)) == "run-1"
    assert asyncio.run(store.find_active_mystic_run_id(member.user_id)) == "run-1"
    assert reward_count(asyncio.run(store.get_user(leader.user_id)), "普通秘境令牌") == 0
    assert reward_count(asyncio.run(store.get_user(member.user_id)), "普通秘境令牌") == 0


def test_reward_settlement_is_idempotent_after_retry() -> None:
    store, run = store_with_completed_run()
    settlement = MysticSettlement(
        settlement_id="mystic:run-1:complete",
        rewards_by_user={"leader": [{"category": "灵石", "name": "灵石", "amount": 100}]},
    )

    asyncio.run(store.settle_mystic_run(run.run_id, settlement))
    asyncio.run(store.settle_mystic_run(run.run_id, settlement))

    record = asyncio.run(store.get_user("leader"))
    assert record.spirit_stones == 100
    assert record.mystic_settlement_ids == ["mystic:run-1:complete"]


def test_compare_and_swap_rejects_stale_run_revision() -> None:
    store, run = store_with_active_run()
    first = asyncio.run(store.update_mystic_run(run.run_id, 0, lambda item: item))
    with pytest.raises(MysticRunConflict):
        asyncio.run(store.update_mystic_run(run.run_id, 0, lambda item: item))
    assert first.revision == 1
```

Also cover restart reload, private route lookup, corrupt JSON returning a controlled error, and completion cleanup.

- [ ] **Step 2: Run tests and verify storage APIs are missing**

Run:

```powershell
uv run pytest tests/test_mystic_storage.py -q
```

Expected: FAIL because the run store and new player fields do not exist.

- [ ] **Step 3: Add only the new player index and settlement fields**

Add to `UserRecord` and its `to_dict()`/`from_dict()` paths:

```python
active_mystic_run_id: str | None = None
mystic_settlement_ids: Optional[list[str]] = None
```

Normalize settlement ids with stable order and a maximum retained length of 100. Do not add old-state migration fields.

- [ ] **Step 4: Add the dedicated state file and typed exceptions**

In `JsonStore.__init__`:

```python
self.mystic_file_path = data_dir / "mystic_dungeons.json"
```

Add in `storage.py`:

```python
class MysticRunConflict(RuntimeError):
    """Raised when a persisted run revision changed before update."""


class MysticRunNotFound(LookupError):
    """Raised when a requested persisted run does not exist."""
```

The JSON root must be:

```json
{
  "schema_version": 1,
  "runs": {},
  "encounters": {},
  "active_by_user": {},
  "private_routes": {}
}
```

- [ ] **Step 5: Implement run CRUD and compare-and-swap updates**

Add these exact methods:

- `get_mystic_run(run_id: str) -> MysticDungeonRun | None`
- `list_active_mystic_runs() -> list[MysticDungeonRun]`
- `find_active_mystic_run_id(user_id: str) -> str | None`
- `create_mystic_run(run: MysticDungeonRun, payer_id: str, token_name: str) -> MysticDungeonRun`
- `update_mystic_run(run_id: str, expected_revision: int, updater: Callable[[MysticDungeonRun], MysticDungeonRun | None]) -> MysticDungeonRun`
- `bind_mystic_private_routes(run: MysticDungeonRun) -> None`
- `resolve_mystic_private_route(user_id: str) -> tuple[str, str] | None`
- `close_mystic_run(run_id: str, terminal_phase: DungeonPhase) -> MysticDungeonRun`

`create_mystic_run()` must write a `CREATING` run before charging, deduct the token under the same `JsonStore._lock`, record `entry:{run_id}` in `mystic_settlement_ids`, activate the run, and then write user/run files. On startup, a `CREATING` run with no charge is deleted; a charged `CREATING` run is activated.

- [ ] **Step 6: Implement idempotent multi-user reward settlement**

Use:

```python
@dataclass(frozen=True)
class MysticSettlement:
    settlement_id: str
    rewards_by_user: dict[str, list[dict[str, Any]]]


async def settle_mystic_run(self, run_id: str, settlement: MysticSettlement) -> MysticDungeonRun:
    async with self._lock:
        users = self._read_json(self.user_file_path)
        state = self._read_mystic_state_locked()
        run = self._run_from_state(state, run_id)
        for user_id, rewards in settlement.rewards_by_user.items():
            record = UserRecord.from_dict(dict(users.get(user_id) or {"user_id": user_id}))
            ids = list(record.mystic_settlement_ids or [])
            if settlement.settlement_id in ids:
                continue
            apply_mystic_rewards(record, rewards)
            record.mystic_settlement_ids = (ids + [settlement.settlement_id])[-100:]
            users[user_id] = sanitize_user_record_data(record.to_dict())
        run.phase = DungeonPhase.COMPLETED
        self._write_json(self.user_file_path, users)
        self._write_mystic_state_locked(state, run)
        return run
```

`apply_mystic_rewards()` must handle spirit stones, cultivation experience, fishing chances, and item rewards through existing domain helpers.

- [ ] **Step 7: Run storage tests**

Run:

```powershell
uv run pytest tests/test_mystic_storage.py -q
```

Expected: PASS for entry charging, active indexes, CAS revisions, route lookup, restart reload, and duplicate settlement.

---

### Task 6: Instantiate Node Content, Personal Rewards, And Tokens

**Files:**
- Modify: `mystic_dungeon.py`
- Modify: `domain.py`
- Modify: `admin.py`
- Modify: `tests/test_mystic_dungeon.py`
- Modify: `tests/test_domain_features.py`

- [ ] **Step 1: Write failing deterministic content and token tests**

Add tests:

```python
def test_same_content_seed_builds_same_node_categories() -> None:
    config = default_mystic_gameplay_config()
    first = factory.instantiate(template, 32, content_seed=991, config=config)
    second = factory.instantiate(template, 32, content_seed=991, config=config)
    assert first.node_contents == second.node_contents


def test_reward_node_rolls_once_per_fixed_member() -> None:
    run = started_team_run("leader", "member")
    result = service.resolve_reward_node(run, node_id="node-9")
    assert set(result.rewards_by_user) == {"leader", "member"}
    assert len(result.rewards_by_user["leader"]) == 1
    assert len(result.rewards_by_user["member"]) == 1


def test_revisited_resolved_node_does_not_reward_twice() -> None:
    run = started_team_run("leader", "member")
    service.resolve_reward_node(run, node_id="node-9")
    repeated = service.resolve_reward_node(run, node_id="node-9")
    assert repeated.rewards_by_user == {}


def test_signin_can_grant_configured_normal_token() -> None:
    domain.apply_admin_config({"mystic": {"signin_normal_token_count": 1}})
    record = signed_in_record()
    domain.apply_signin(record, date(2026, 7, 16))
    assert reward_count(record, "普通秘境令牌") == 1
```

- [ ] **Step 2: Run focused tests and confirm failures**

Run:

```powershell
uv run pytest tests/test_mystic_dungeon.py tests/test_domain_features.py -q
```

Expected: FAIL on content factory, reward ledger, and token configuration.

- [ ] **Step 3: Add token definitions without adding them to fishing drops**

In `domain.py` define:

```python
MYSTIC_TOKEN_DEFINITIONS = {
    "普通秘境令牌": {
        "tier": "玄阶",
        "grade": "中品",
        "category": "杂物",
        "description": "开启普通秘境副本的凭证。",
    },
    "高风险秘境令牌": {
        "tier": "地阶",
        "grade": "上品",
        "category": "杂物",
        "description": "开启高风险秘境副本的凭证。",
    },
}


def mystic_token_reward(name: str) -> dict[str, Any]:
    definition = MYSTIC_TOKEN_DEFINITIONS[name]
    return {"name": name, **definition}
```

Merge these definitions into `admin_item_catalog()` but not `FISHING_REWARDS`.

- [ ] **Step 4: Add deterministic node content types and factory**

```python
@dataclass(frozen=True)
class MapSizeRule:
    minimum_boss_realm_index: int
    node_count: int


@dataclass(frozen=True)
class MysticGameplayConfig:
    map_size_rules: tuple[MapSizeRule, ...]
    min_map_size: int
    max_map_size: int
    normal_node_weights: dict[str, float]
    high_risk_node_weights: dict[str, float]
    normal_branch_density: float
    high_risk_branch_density: float
    high_risk_loop_count: int
    consecutive_combat_limit: int
    ordinary_monster_hp_multiplier: float
    boss_hp_multiplier: float
    reward_multiplier: float
    damage_growth_per_ten_rounds: float
    encounter_response_seconds: int
    battle_prepare_seconds: int
    player_action_seconds: int
    boss_vote_seconds: int
    leader_inactive_seconds: int
    leader_transfer_vote_seconds: int
    rescue_wait_seconds: int
    signin_normal_token_count: int
    signin_high_risk_token_count: int
    daily_task_normal_token_count: int
    daily_task_high_risk_token_count: int


@dataclass(frozen=True)
class DungeonNodeContent:
    node_id: str
    kind: NodeKind
    event_id: str
    visible_label: str
    payload: dict[str, Any]
```

Create `MysticContentFactory` and implement `instantiate(template: DungeonMapTemplate, map_size: int, content_seed: int, config: MysticGameplayConfig) -> dict[str, DungeonNodeContent]` with the deterministic rules below.

Add `default_mystic_gameplay_config() -> MysticGameplayConfig` in the same step. Task 13 adds mapping validation and admin serialization to this same type; it must not define a second config class.

Use `random.Random(content_seed)` only inside the factory. Force start/Boss/required safe nodes, enforce the consecutive-combat cap, and choose all other categories from normalized configured weights.

- [ ] **Step 5: Add per-user temporary reward ledgers**

```python
@dataclass
class DungeonRewardLedger:
    rewards_by_user: dict[str, list[dict[str, Any]]] = field(default_factory=dict)
    settled_node_keys: set[str] = field(default_factory=set)

    def add_personal(self, user_id: str, node_id: str, reward: dict[str, Any]) -> bool:
        key = f"{node_id}:{user_id}"
        if key in self.settled_node_keys:
            return False
        self.settled_node_keys.add(key)
        self.rewards_by_user.setdefault(user_id, []).append(dict(reward))
        return True
```

Serialize `settled_node_keys` as a sorted list. Combat drops are added by `MysticBattleService`; resource/reward nodes call `add_personal()` once for every fixed member.

- [ ] **Step 6: Apply token grant configuration**

Add default config keys:

```python
"signin_normal_token_count": 0,
"signin_high_risk_token_count": 0,
"daily_task_normal_token_count": 0,
"daily_task_high_risk_token_count": 0,
```

Update existing signin and daily-task reward finalization functions to append the configured counts. Counts must be clamped to `0..10` in config validation.

- [ ] **Step 7: Run node and token tests**

Run:

```powershell
uv run pytest tests/test_mystic_dungeon.py tests/test_domain_features.py -q
```

Expected: PASS for deterministic content, no duplicate node rewards, per-member rewards, and configurable tokens.

---

### Task 7: Implement Incremental PVE Encounter And Boss State

**Files:**
- Create: `mystic_battle.py`
- Create: `tests/test_mystic_battle.py`
- Modify: `mystic_dungeon.py`
- Modify: `storage.py`
- Modify: `tests/test_mystic_storage.py`

- [ ] **Step 1: Write failing ordinary encounter tests**

```python
def test_two_players_damage_one_shared_monster_and_receive_individual_retaliation() -> None:
    encounter = ordinary_encounter(monster_hp=1_000, participants=("a", "b"))
    service.submit_action(encounter, "a", "普通攻击", action_id="a:1")
    service.submit_action(encounter, "b", "普通攻击", action_id="b:1")
    assert encounter.shared_monster_hp < 1_000
    assert encounter.participants["a"].hp < encounter.participants["a"].max_hp
    assert encounter.participants["b"].hp < encounter.participants["b"].max_hp


def test_duplicate_action_id_does_not_damage_twice() -> None:
    encounter = ordinary_encounter(monster_hp=1_000, participants=("a",))
    first = service.submit_action(encounter, "a", "普通攻击", action_id="a:1")
    second = service.submit_action(encounter, "a", "普通攻击", action_id="a:1")
    assert second == first
    assert encounter.action_ids == {"a:1"}


def test_defeated_participant_still_gets_loot_after_team_victory() -> None:
    encounter = encounter_where_a_falls_and_b_wins()
    result = service.finish_encounter(encounter)
    assert set(result.eligible_loot_user_ids) == {"a", "b"}
```

- [ ] **Step 2: Write failing Boss formula and continuation tests**

```python
def test_team_boss_has_h_times_n_total_hp_and_h_per_segment() -> None:
    encounter = service.create_boss_encounter(base_hp=500_000, member_ids=("a", "b", "c"))
    assert encounter.total_initial_hp == 1_500_000
    assert [segment.initial_hp for segment in encounter.boss_segments.values()] == [500_000] * 3


def test_continue_keeps_hp_and_allows_cleared_member_to_assist() -> None:
    encounter = partially_failed_boss_encounter()
    before = encounter.to_dict()
    service.open_boss_continuation(encounter, approvals={"a": True, "b": True, "c": False})
    service.join_boss_assist(encounter, helper_id="a", segment_id="segment:c")
    assert encounter.boss_segments["segment:c"].hp == before["boss_segments"]["segment:c"]["hp"]
    assert encounter.participants["a"].hp == before["participants"]["a"]["hp"]
```

Also test 2-player unanimous vote, 3-player majority vote, zero-HP rejection, all-zero immediate failure, and multiple helpers on one segment.

- [ ] **Step 3: Run tests and verify the module is missing**

Run:

```powershell
uv run pytest tests/test_mystic_battle.py -q
```

Expected: FAIL because `mystic_battle.py` does not exist.

- [ ] **Step 4: Define encounter and participant state**

```python
class EncounterKind(StrEnum):
    ORDINARY = "ordinary"
    BOSS = "boss"
    RESCUE = "rescue"


class EncounterPhase(StrEnum):
    AWAITING_RESPONSE = "awaiting_response"
    PREPARING = "preparing"
    ACTIVE = "active"
    AWAITING_CONTINUE_VOTE = "awaiting_continue_vote"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class DungeonBattleParticipant:
    user_id: str
    state: CombatRuntimeState
    equipment_snapshot: dict[str, Any]
    valid_action_count: int = 0
    defeated: bool = False
    auto_battle: bool = False
    target_segment_id: str | None = None


@dataclass
class BossHealthSegment:
    segment_id: str
    owner_user_id: str
    initial_hp: int
    hp: int
    cleared: bool = False


@dataclass
class DungeonEncounter:
    encounter_id: str
    run_id: str
    kind: EncounterKind
    phase: EncounterPhase
    monster_record: dict[str, Any]
    shared_monster_hp: int
    participants: dict[str, DungeonBattleParticipant]
    boss_segments: dict[str, BossHealthSegment] = field(default_factory=dict)
    action_ids: set[str] = field(default_factory=set)
    cached_action_results: dict[str, dict[str, Any]] = field(default_factory=dict)
    shared_round: int = 0
    damage_multiplier: float = 1.0
    revision: int = 0


@dataclass(frozen=True)
class EncounterResult:
    completed: bool
    failed: bool
    needs_rescue: bool
    eligible_loot_user_ids: tuple[str, ...]
```

Implement explicit `to_dict()` and `from_dict()` for `DungeonEncounter`, `DungeonBattleParticipant`, and `BossHealthSegment`. Serialize enums as strings, sets as sorted lists, and `CombatRuntimeState` as plain scalar fields so encounters can be stored in the Task 5 `encounters` collection.

Add these store methods after the encounter types exist:

- `get_mystic_encounter(encounter_id: str) -> DungeonEncounter | None`
- `list_active_mystic_encounters() -> list[DungeonEncounter]`
- `create_mystic_encounter(encounter: DungeonEncounter) -> DungeonEncounter`
- `update_mystic_encounter(encounter_id: str, expected_revision: int, updater: Callable[[DungeonEncounter], DungeonEncounter | None]) -> DungeonEncounter`
- `delete_mystic_encounter(encounter_id: str) -> None`

Extend `tests/test_mystic_storage.py` with encounter round-trip and stale-revision tests before implementing these methods.

Create `MysticBattleService` with constructor `MysticBattleService(config: MysticGameplayConfig, now: Callable[[], datetime])` and these exact public methods: `submit_action`, `resolve_timed_out_action`, `set_auto_battle`, `run_auto_actions`, the ordinary encounter methods in Step 6, and the Boss methods in Step 7.

- [ ] **Step 5: Implement serialized action resolution**

`MysticBattleService.submit_action()` must:

1. Reject non-active phases and defeated actors.
2. Return the cached result for an existing `action_id`.
3. Call `domain.resolve_combat_action()` with the participant state.
4. Apply configured damage growth after every 10 shared rounds.
5. Subtract damage from the shared monster or target Boss segment.
6. If the target survives, choose one legal monster action and resolve its damage only against the actor.
7. Mark actor or target defeated/cleared.
8. Cache the result under `action_id`.

Use a service-level lock key supplied by the caller; persistence still uses `JsonStore._lock` and run revision checks.

- [ ] **Step 6: Implement ordinary batches and loot eligibility**

Add these exact methods:

- `create_ordinary_encounter(encounter_id: str, run_id: str, monster_record: UserRecord, fixed_member_ids: Sequence[str]) -> DungeonEncounter`
- `join_ordinary_encounter(encounter: DungeonEncounter, user_id: str, record: UserRecord, equipment_snapshot: dict[str, Any]) -> None`
- `begin_preparation(encounter: DungeonEncounter, deadline: datetime) -> None`
- `begin_next_response_batch(encounter: DungeonEncounter, deadline: datetime) -> tuple[str, ...]`
- `finish_encounter(encounter: DungeonEncounter) -> EncounterResult`

`finish_encounter()` returns every fixed participant with `valid_action_count > 0`, even if defeated. If all fixed members have been attempted and the monster survives, return `needs_rescue=True` with the remaining monster snapshot.

- [ ] **Step 7: Implement Boss segments and assistance**

`create_boss_encounter(base_hp, member_ids)` must create one segment per initial member with `initial_hp == base_hp`. Continuation copies no state; it mutates the existing encounter after a successful vote. Helpers may select only uncleared segments, and zero-HP helpers are rejected.

- [ ] **Step 8: Implement auto battle and action timeout**

`set_auto_battle()` must reject players whose `realm_index` is less than or equal to the enemy realm index. `run_auto_actions()` repeatedly selects a legal action for only that participant, calls `submit_action()` with a new deterministic action id, persists after each action through the caller, and yields to the event loop between turns. `resolve_timed_out_action()` uses the same legal-action selector for one turn. Neither method may skip shared locks or compute a direct final winner.

- [ ] **Step 9: Run battle tests**

Run:

```powershell
uv run pytest tests/test_combat_turns.py tests/test_mystic_battle.py -q
```

Expected: PASS for shared HP, per-player retaliation, duplicate actions, loot eligibility, `H × N`, vote thresholds, HP inheritance, and assistance.

---

### Task 8: Render Full Maps And Publish The Boss Label

**Files:**
- Create: `mystic_cards.py`
- Create: `tests/test_mystic_cards.py`
- Create: `tools/render_mystic_map_preview.py`
- Create: `assets/mystic_dungeon_ui/boss_label.png`
- Modify only if necessary: `cards.py`

- [ ] **Step 1: Copy the approved BOSS label into the runtime asset path**

Source:

```text
ui-sprite-runs/2026-07-16-mystic-boss-label/boss-label-final.png
```

Destination:

```text
assets/mystic_dungeon_ui/boss_label.png
```

Use `apply_patch` for code and manifest changes. The binary copy is a mechanical asset publication step and must preserve transparency.

- [ ] **Step 2: Write failing renderer tests**

```python
def test_renderer_contains_all_active_nodes_for_24_and_48_sizes() -> None:
    for size in (24, 48):
        model = render_model(size=size, team_size=3)
        image = renderer.render(model)
        assert image.size == (1600, 900)
        for node in model.nodes:
            assert renderer.node_box(node).within(image.size)


def test_route_colors_and_icon_sizes_are_stable() -> None:
    model = colored_route_model()
    image = renderer.render(model)
    assert sampled_color(image, model.traversed_edge_midpoint) == renderer.TRAVERSED_GREEN
    assert sampled_color(image, model.next_edge_midpoint) == renderer.NEXT_RED
    assert renderer.REGULAR_NODE_SIZE == 20
    assert renderer.BOSS_NODE_SIZE == 25


def test_rendered_map_is_not_blank() -> None:
    image = renderer.render(render_model(size=48, team_size=2))
    colors = image.convert("RGB").getcolors(maxcolors=image.width * image.height)
    assert colors is not None
    assert len(colors) > 50
```

- [ ] **Step 3: Run tests and confirm the renderer is missing**

Run:

```powershell
uv run pytest tests/test_mystic_cards.py -q
```

Expected: FAIL because `mystic_cards.py` does not exist.

- [ ] **Step 4: Implement renderer model and crop calculation**

```python
@dataclass(frozen=True)
class RenderedNode:
    node_id: str
    x: float
    y: float
    kind: NodeKind
    label: str
    boss_portrait_path: Path | None = None


@dataclass(frozen=True)
class RenderedEdge:
    edge_id: str
    source_node_id: str
    target_node_id: str
    state: str


@dataclass(frozen=True)
class MysticMapRenderModel:
    title: str
    subtitle: str
    background_path: Path
    nodes: tuple[RenderedNode, ...]
    edges: tuple[RenderedEdge, ...]
    current_node_id: str
    team_size: int
    temporary_reward_summary: str


class MysticMapRenderer:
    OUTPUT_SIZE = (1600, 900)
    REGULAR_NODE_SIZE = 20
    BOSS_NODE_SIZE = 25
    TRAVERSED_GREEN = (60, 190, 95, 230)
    NEXT_RED = (224, 62, 62, 240)
    FUTURE_GRAY = (220, 225, 230, 150)
```

Implement these exact methods in the same class: `render(model: MysticMapRenderModel) -> Image.Image`, `crop_box(model: MysticMapRenderModel) -> tuple[int, int, int, int]`, and `text_fallback(model: MysticMapRenderModel) -> str`.

The crop box must include every active normalized coordinate plus margin, expand to 16:9, clamp to the 3840x2160 source, and scale once to 1600x900.

- [ ] **Step 5: Draw required node and route states**

- Draw future edges first as gray-white dashed lines.
- Draw traversed edges as green solid lines.
- Draw all legal current-to-next edges as red solid lines.
- Draw regular nodes as 20x20 translucent icons: `?`, crossed swords, green chest, trap, and rest glyphs.
- Draw the current position as a 20x20 yin-yang formation with an adjacent `2/3` count for teams.
- Draw Boss portrait at 25x25 and place `boss_label.png` above the avatar; the label must not affect route collision bounds.

- [ ] **Step 6: Add deterministic preview tool**

`tools/render_mystic_map_preview.py` must accept:

```powershell
uv run python tools/render_mystic_map_preview.py --theme ancient_sect_ruins --size 24 --team-size 2 --output C:\tmp\mystic-24.png
uv run python tools/render_mystic_map_preview.py --theme green_mystic_shadow --size 48 --team-size 3 --output C:\tmp\mystic-48.png
```

It must load the real catalog, mark a deterministic traversed path, and save a nonblank PNG.

- [ ] **Step 7: Run renderer tests and inspect both previews**

Run:

```powershell
uv run pytest tests/test_mystic_cards.py -q
uv run python tools/render_mystic_map_preview.py --theme ancient_sect_ruins --size 24 --team-size 2 --output C:\tmp\mystic-24.png
uv run python tools/render_mystic_map_preview.py --theme green_mystic_shadow --size 48 --team-size 3 --output C:\tmp\mystic-48.png
```

Expected: tests PASS; both images are 1600x900, nonblank, and contain no node/label overlap.

---

### Task 9: Wire Group Lobbies, Movement, And Persistent Private Routes

**Files:**
- Create: `mystic_runtime.py`
- Modify: `__init__.py:353-484, 3130-3395, 4338-4420`
- Create: `tests/test_mystic_integration.py`

- [ ] **Step 1: Write failing command parser and coordinator tests**

Add service-level tests that do not import a live OneBot adapter:

```python
def test_group_commands_create_join_ready_start_and_roll() -> None:
    coordinator = integration_coordinator()
    coordinator.handle_group("100", "leader", "创建秘境队伍 普通")
    coordinator.handle_group("100", "member", "加入秘境队伍")
    coordinator.handle_group("100", "leader", "秘境准备")
    coordinator.handle_group("100", "member", "秘境准备")
    started = coordinator.handle_group("100", "leader", "开始秘境")
    moved = coordinator.handle_group("100", "leader", "投骰 4")
    assert started.run.phase is DungeonPhase.READY_TO_ROLL
    assert moved.map_required is True


def test_only_leader_can_roll_or_choose_branch() -> None:
    coordinator = started_team_coordinator()
    denied = coordinator.handle_group("100", "member", "投骰 3")
    assert denied.error == "只有队长可以投骰。"


def test_private_command_resolves_persisted_run_route_after_new_coordinator_instance() -> None:
    first = started_team_coordinator()
    run_id = first.active_run_id("leader")
    second = integration_coordinator(store=first.store)
    route = second.resolve_private_context("leader")
    assert route.run_id == run_id
    assert route.source_group_id == "100"
```

- [ ] **Step 2: Run integration tests and verify parser/coordinator APIs are missing**

Run:

```powershell
uv run pytest tests/test_mystic_integration.py -q
```

Expected: FAIL on missing command parsing and coordinator APIs.

- [ ] **Step 3: Add pure command parsing**

In `mystic_runtime.py` add:

```python
class MysticGroupAction(StrEnum):
    STATUS = "status"
    CREATE_SOLO = "create_solo"
    CREATE_TEAM = "create_team"
    JOIN = "join"
    LEAVE_LOBBY = "leave_lobby"
    READY = "ready"
    START = "start"
    MAP = "map"
    ROLL = "roll"
    CHOOSE_BRANCH = "choose_branch"
    RESPOND = "respond"
    VOTE_CONTINUE = "vote_continue"
    VOTE_TRANSFER = "vote_transfer"
    VOTE_ABANDON = "vote_abandon"


@dataclass(frozen=True)
class MysticParsedCommand:
    action: MysticGroupAction
    argument: str = ""


def parse_mystic_group_command(text: str) -> MysticParsedCommand | None:
    normalized = " ".join(text.strip().split())
    return _GROUP_COMMAND_PARSER.parse(normalized)


def parse_mystic_private_command(text: str) -> str | None:
    normalized = " ".join(text.strip().split())
    return normalized if _PRIVATE_COMMAND_PARSER.accepts(normalized) else None
```

Define `_GROUP_COMMAND_PARSER` and `_PRIVATE_COMMAND_PARSER` in the same step as small table-driven parser classes; the tests above are the required accepted/rejected command set.

Also define:

```python
@dataclass(frozen=True)
class DungeonEntryOffer:
    mode: DungeonMode
    risk: DungeonRisk
    theme_id: str
    boss_realm_index: int
    insight: bool = False


class MysticCommandCoordinator:
    def __init__(
        self,
        store: JsonStore,
        dungeon_service: MysticDungeonService,
        battle_service: MysticBattleService,
        renderer: MysticMapRenderer,
    ) -> None:
        self.store = store
        self.dungeon_service = dungeon_service
        self.battle_service = battle_service
        self.renderer = renderer
```

Add typed result objects for group/private transport containing message text, optional image bytes, private-message targets, updated run revision, and error text. The NoneBot handlers call this coordinator and contain no game-rule branches.

The parser must accept the documented Chinese commands, Arabic dice/branch numbers, and `同意/拒绝`; it must not consume unrelated normal duel or equipment commands.

- [ ] **Step 4: Add thin group/private matchers**

In `__init__.py` register:

```python
async def is_mystic_group_message(event: MessageEvent) -> bool:
    return isinstance(event, GroupMessageEvent) and parse_mystic_group_command(normalized_plain_text(event)) is not None


async def is_mystic_private_message(event: MessageEvent) -> bool:
    if not isinstance(event, PrivateMessageEvent):
        return False
    action = parse_mystic_private_command(normalized_plain_text(event))
    if action is None:
        return False
    return await store.resolve_mystic_private_route(event.get_user_id()) is not None


mystic_group_cmd = on_message(rule=Rule(is_mystic_group_message), priority=8, block=True)
mystic_private_cmd = on_message(rule=Rule(is_mystic_private_message), priority=6, block=True)
```

These priorities must precede generic managed commands but not steal non-mystic equipment commands.

- [ ] **Step 5: Implement lobby and movement transport**

`handle_mystic_group()` must:

1. Call `remember_group_member()`.
2. Load the active run or create a lobby through `MysticDungeonService`.
3. Use store CAS updates for join, ready, start, roll, branch, transfer, and abandon actions.
4. On start, call `create_mystic_run()` with the correct normal/high-risk token.
5. Persist private routes for all fixed members.
6. Render/send the full map after start, roll, and branch completion.
7. Send text fallback if rendering or image delivery fails.

Do not store an in-memory `mystic_tables` dictionary. In-memory task handles may cache deadlines, but persisted run state is authoritative.

- [ ] **Step 6: Keep Tianji entry as a new-engine single offer**

Replace the old `draw_tianji_mystic_entrances()` result consumption with a `DungeonEntryOffer` that sets `mode=SOLO`, `insight=True`, and the same source group. It creates a normal new-engine run and never writes `record.mystic_realm`.

- [ ] **Step 7: Run integration tests**

Run:

```powershell
uv run pytest tests/test_mystic_integration.py tests/test_mystic_storage.py tests/test_mystic_dungeon.py -q
```

Expected: PASS for lobby, team lock, leader movement, branch choice, private route persistence, and Tianji entry.

---

### Task 10: Wire Ordinary Encounters And Real PVE Rescue

**Files:**
- Modify: `mystic_battle.py`
- Modify: `mystic_runtime.py`
- Modify: `storage.py:342-383`
- Modify: `__init__.py:4000-4080` and new mystic handlers
- Modify: `tests/test_mystic_battle.py`
- Modify: `tests/test_mystic_storage.py`
- Modify: `tests/test_mystic_integration.py`

- [ ] **Step 1: Write failing end-to-end ordinary encounter tests**

```python
def test_team_combat_opens_group_response_then_private_preparation() -> None:
    coordinator = coordinator_landed_on_combat_node()
    opened = coordinator.resolve_current_node()
    joined = coordinator.handle_group("100", "leader", "应战")
    assert opened.run.phase is DungeonPhase.AWAITING_ENCOUNTER_RESPONSE
    assert joined.private_messages == (("leader", "秘境配装"),)


def test_unattempted_member_takes_over_remaining_hp() -> None:
    coordinator = coordinator_after_first_batch_defeat(monster_hp=300)
    coordinator.handle_group("100", "member", "应战")
    encounter = coordinator.active_encounter()
    assert encounter.shared_monster_hp == 300


def test_all_fixed_members_defeated_creates_open_rescue_without_paying_on_take() -> None:
    coordinator = coordinator_after_every_member_defeat(monster_hp=250)
    request = coordinator.open_rescue(reward_stones=1_000)
    coordinator.take_rescue(request.request_id, "rescuer")
    assert coordinator.user("rescuer").spirit_stones == 0
    coordinator.complete_rescue(request.request_id, "rescuer")
    assert coordinator.user("rescuer").spirit_stones == 1_000
```

- [ ] **Step 2: Run focused tests and confirm handler/storage failures**

Run:

```powershell
uv run pytest tests/test_mystic_battle.py tests/test_mystic_storage.py tests/test_mystic_integration.py -q
```

Expected: FAIL because response windows, private preparation, and rescue completion do not exist.

- [ ] **Step 3: Extend rescue request persistence**

Replace the old immediate-take schema with:

```python
@dataclass
class MysticRescueRequest:
    request_id: str
    run_id: str
    encounter_id: str
    group_id: str
    requester_id: str
    requester_name: str
    reward_stones: int
    monster_snapshot: dict[str, Any]
    remaining_hp: int
    deadline: str
    status: str = "open"
    active_rescuer_id: str | None = None
    attempted_rescuer_ids: list[str] = field(default_factory=list)
```

Add these exact store methods:

- `create_rescue_request(request: MysticRescueRequest) -> MysticRescueRequest`
- `list_rescue_requests(group_id: str) -> list[MysticRescueRequest]`
- `take_rescue_request(group_id: str, request_id: str, rescuer_id: str) -> MysticRescueRequest | None`
- `fail_rescue_attempt(request_id: str, rescuer_id: str) -> MysticRescueRequest`
- `complete_rescue_request(request_id: str, rescuer_id: str) -> MysticRescueRequest`
- `expire_rescue_request(request_id: str) -> MysticRescueRequest`

`take_rescue_request()` never pays. `complete_rescue_request()` pays exactly once using a settlement id and clears the original encounter node.

- [ ] **Step 4: Implement response and preparation deadlines**

When a combat node resolves:

- Solo: add the only member immediately and enter 60-second preparation.
- Team: persist `AWAITING_RESPONSE` and a deadline, accept one or more fixed members, and allow the leader to close early only after at least one response.
- If the team response window expires with no participants, keep the node unresolved and return the run to a blocked response state; do not allow rolling.
- At preparation expiry, snapshot current equipment and create `CombatRuntimeState` for every respondent.

- [ ] **Step 5: Route private combat actions**

`handle_mystic_private()` must accept `普通攻击`, legal technique/ability names, `自动战斗`, and `确认配装`. It resolves the persisted private route, loads the encounter, submits a unique action id derived from `event.message_id`, persists the result, and sends only that participant's battle status in private.

After an ordinary victory, send one group summary and full map, add combat drops only for `valid_action_count > 0`, and restore `READY_TO_ROLL`.

- [ ] **Step 6: Implement fixed-member handoff and external rescue**

When a batch ends with surviving monster HP:

- Reopen group response only for fixed members with no prior valid action.
- Preserve monster HP; reset batch-local buffs, debuffs, mana, and cooldowns.
- After every fixed member has failed, set run phase `AWAITING_RESCUE`.
- Current leader creates/pays the rescue request in the source group.
- Rescuer fights privately against the saved monster HP.
- Success restores the original run at the cleared node; failure reopens the request for a different rescuer.

- [ ] **Step 7: Run ordinary encounter and rescue tests**

Run:

```powershell
uv run pytest tests/test_mystic_battle.py tests/test_mystic_storage.py tests/test_mystic_integration.py -q
```

Expected: PASS for response, preparation, shared HP, private actions, batch handoff, delayed rescue payout, and node restoration.

---

### Task 11: Wire Segmented Boss Combat And Continuation

**Files:**
- Modify: `mystic_battle.py`
- Modify: `mystic_dungeon.py`
- Modify: `mystic_runtime.py`
- Modify: `storage.py`
- Modify: `__init__.py`
- Modify: `tests/test_mystic_battle.py`
- Modify: `tests/test_mystic_integration.py`

- [ ] **Step 1: Write failing Boss transport tests**

```python
def test_boss_node_privately_prepares_every_fixed_member() -> None:
    coordinator = coordinator_landed_on_boss(team_size=3, base_hp=500_000)
    result = coordinator.resolve_current_node()
    assert set(user_id for user_id, _title in result.private_messages) == {"a", "b", "c"}
    assert sum(segment.initial_hp for segment in coordinator.active_encounter().boss_segments.values()) == 1_500_000


def test_three_player_majority_continue_allows_cleared_member_to_help_failed_segment() -> None:
    coordinator = coordinator_after_partial_boss_failure()
    coordinator.handle_group("100", "a", "秘境续战 同意")
    result = coordinator.handle_group("100", "b", "秘境续战 同意")
    coordinator.handle_group("100", "a", "应战 c")
    assert result.vote_passed is True
    assert coordinator.participant("a").target_segment_id == "segment:c"


def test_all_zero_hp_fails_without_opening_vote() -> None:
    coordinator = coordinator_after_total_boss_wipe()
    result = coordinator.finish_boss_batch()
    assert result.run.phase is DungeonPhase.FAILED
    assert result.vote_created is False
```

- [ ] **Step 2: Run tests and confirm transport behavior is missing**

Run:

```powershell
uv run pytest tests/test_mystic_battle.py tests/test_mystic_integration.py -q
```

Expected: FAIL on Boss private preparation, continuation routing, and terminal settlement.

- [ ] **Step 3: Start single and team Boss encounters from the landing node**

- Solo creates one segment with `initial_hp == H`, but no continuation vote is allowed after defeat.
- Team creates `N` segments with `initial_hp == H`, so total HP is exactly `H × N`.
- Assign each segment to one fixed member and persist `boss_segment_id` on the run member state.
- Send every member a 60-second private preparation panel.

- [ ] **Step 4: Open and resolve continuation votes**

Persist a `DungeonVote` with:

Reuse the `DungeonVote` and `VoteKind.BOSS_CONTINUE` definitions created in Task 4. Persist approvals, rejections, eligible ids, and the absolute deadline on the run/encounter state.

Thresholds are fixed: 2-player team requires 2 approvals; 3-player team requires 2 approvals. Missing votes count as rejection at expiry. Do not copy or reset participant/segment HP when the vote passes.

- [ ] **Step 5: Route helpers to uncleared segments**

Accept `应战 队员编号` only from a living member whose own segment is cleared. Resolve the supplied name or numeric roster index to an uncleared segment, set `target_segment_id`, create a fresh action deadline using the helper's inherited HP/mana/cooldowns, and allow multiple helpers to share that segment lock.

- [ ] **Step 6: Settle success or failure exactly once**

When every segment reaches zero:

1. Add the team Boss reward to every fixed member's temporary ledger.
2. Build settlement id `mystic:{run_id}:complete`.
3. Call `settle_mystic_run()` once.
4. Send the final group result and full map.

On failed vote, solo defeat, all-zero wipe, or abandon, call `close_mystic_run()` without applying temporary rewards.

- [ ] **Step 7: Run Boss tests**

Run:

```powershell
uv run pytest tests/test_mystic_battle.py tests/test_mystic_storage.py tests/test_mystic_integration.py -q
```

Expected: PASS for single Boss failure, `H × N`, segment assignment, majority voting, strict HP inheritance, assistance, and idempotent final settlement.

---

### Task 12: Recover Deadlines And Remove The Legacy Mystic Runtime

**Files:**
- Modify: `__init__.py:353-484, 3130-3395, 4000-4420`
- Modify: `domain.py:2472-2800, 8420-9470`
- Modify: `mystic_runtime.py`
- Modify: `storage.py`
- Modify: `tests/test_domain_features.py`
- Modify: `tests/test_mystic_integration.py`
- Modify: `tests/test_xiuxian_admin_rewrite.py`

- [ ] **Step 1: Write failing restart recovery tests**

```python
def test_restart_expires_response_and_vote_using_original_deadline() -> None:
    store = persisted_store_with_expired_response_and_vote()
    coordinator = integration_coordinator(store=store, now=fixed_now_after_deadlines())
    recovered = asyncio.run(coordinator.recover_active_runs())
    assert recovered.response_expirations == 1
    assert recovered.vote_expirations == 1


def test_restart_restores_private_routes_and_active_action_deadlines() -> None:
    store = persisted_store_with_active_encounter()
    coordinator = integration_coordinator(store=store)
    asyncio.run(coordinator.recover_active_runs())
    assert coordinator.resolve_private_context("a").run_id == "run-1"
    assert coordinator.scheduled_deadline_count == 1
```

Add a source-level assertion that the removed legacy symbols are absent from runtime files.

- [ ] **Step 2: Run recovery and cleanup tests**

Run:

```powershell
uv run pytest tests/test_mystic_integration.py tests/test_domain_features.py tests/test_xiuxian_admin_rewrite.py -q
```

Expected: FAIL because recovery scheduling exists only for in-memory legacy entry timeouts and old symbols remain.

- [ ] **Step 3: Add startup recovery**

Add `recover_mystic_dungeons()` and call it from the existing `@driver.on_startup` function after config application:

```python
async def recover_mystic_dungeons() -> None:
    for run in await store.list_active_mystic_runs():
        await store.bind_mystic_private_routes(run)
        await mystic_coordinator.recover_run(run)
```

`recover_run()` must compare absolute persisted deadlines with `local_now()`, immediately apply expired transitions, and schedule only future deadlines. Each deadline callback re-reads the run and expected revision before mutating.

- [ ] **Step 4: Remove legacy player fields**

Delete these `UserRecord` fields and their serialization branches:

```text
mystic_realm
last_failed_mystic_realm
mystic_boss_successes
mystic_boss_daily_date
mystic_boss_daily_attempts
mystic_boss_daily_bonus
mystic_boss_week_key
mystic_boss_week_attempts
mystic_boss_week_claimed
```

Keep only the new `active_mystic_run_id` and `mystic_settlement_ids`. Existing raw JSON keys are ignored; do not migrate or refund them.

- [ ] **Step 5: Remove the old ten-exploration domain block**

Move any still-needed theme text, type constants, and reward pool data to `mystic_dungeon.py`, then delete the legacy functions from `mystic_realm_title()` through `explore_mystic_realm()` that implement options, step counters, daily Boss attempts, defeat penalties, and ten-run reward folding.

Remove `MYSTIC_REALM_MAX_STEPS`, old Boss daily/weekly constants, and any config globals used only by that block.

- [ ] **Step 6: Remove legacy matchers and help text**

Delete:

```text
pending_mystic_entries
send_mystic_timeout_notice
MYSTIC_EXPLORE_PREFIXES
is_mystic_entry_reply
is_mystic_explore_message
mystic_entry_reply matcher
mystic_explore matcher
handle_mystic_entry_reply
handle_mystic_explore
send_mystic_boss_duel_report
```

Replace old help strings such as `探索 1` and “十次探索” with the new single/team, roll, branch, response, and private battle commands.

- [ ] **Step 7: Invalidate old rescue records without migration**

Add `schema_version: 2` to new rescue storage. When the old file has no matching schema, treat it as empty and overwrite only when a new rescue is created. Do not pay, convert, or refund old requests.

- [ ] **Step 8: Run cleanup scans and recovery tests**

Run:

```powershell
rg -n "MYSTIC_REALM_MAX_STEPS|record\.mystic_realm|last_failed_mystic_realm|探索 编号|十次探索" __init__.py domain.py storage.py tests
uv run pytest tests/test_mystic_integration.py tests/test_domain_features.py tests/test_mystic_storage.py -q
```

Expected: `rg` returns no runtime references; tests PASS for restart recovery and new state serialization.

---

### Task 13: Add Validated Mystic Configuration And API

**Files:**
- Modify: `mystic_dungeon.py`
- Modify: `admin.py:135-318, 560-665`
- Modify: `tests/test_admin_routes.py`

- [ ] **Step 1: Write failing default, validation, and route tests**

Add tests:

```python
def test_default_mystic_config_exposes_map_sizes_and_timeouts() -> None:
    manager = manager_in_temp_dir()
    payload = manager.mystic_payload()
    assert [item["node_count"] for item in payload["map_size_rules"]] == [24, 28, 32, 36, 40, 44, 48]
    assert payload["encounter_response_seconds"] == 60
    assert payload["battle_prepare_seconds"] == 60
    assert payload["boss_vote_seconds"] == 60


def test_mystic_config_rejects_unsupported_sizes_and_invalid_probability_sum() -> None:
    manager = manager_in_temp_dir()
    invalid = manager.mystic_payload()
    invalid["map_size_rules"][0]["node_count"] = 26
    invalid["normal_node_weights"] = {"random": 0.8, "combat": 0.8}
    with pytest.raises(ValueError, match="node_count|weights"):
        manager.save_mystic_config(invalid)


def test_put_mystic_route_saves_only_mystic_section() -> None:
    client = TestClient(admin.create_admin_app(manager=manager_in_temp_dir()))
    payload = valid_mystic_payload(encounter_response_seconds=45)
    response = client.put("/xiuxian-admin/api/mystic", headers=auth_headers(), json=payload)
    assert response.status_code == 200
    assert response.json()["mystic"]["encounter_response_seconds"] == 45
```

- [ ] **Step 2: Run admin tests and confirm validation/PUT are absent**

Run:

```powershell
uv run pytest tests/test_admin_routes.py -q
```

Expected: FAIL because the payload is legacy-only and `/api/mystic` is GET-only.

- [ ] **Step 3: Add mapping validation to the existing gameplay configuration model**

Add `MysticGameplayConfig.from_mapping()` and `MysticGameplayConfig.to_mapping()` to the config type and `MapSizeRule` created in Task 6. Validation rules are exact: supported sizes only, realm thresholds strictly increasing, node counts nondecreasing, each weight map sums to 1 within `1e-6`, timeouts `10..3600`, multipliers positive, token counts `0..10`, team rules not configurable.

- [ ] **Step 4: Validate and save only the mystic section**

Add to `AdminManager`:

```python
def save_mystic_config(self, data: dict[str, Any]) -> dict[str, Any]:
    validated = MysticGameplayConfig.from_mapping(data)
    config = self.load_config()
    config["mystic"] = validated.to_mapping()
    self.save_config(config)
    self.apply_config()
    return self.mystic_payload()
```

Update `mystic_payload()` to include theme lists, supported sizes, gameplay config, token definitions, and background/template binding status.

- [ ] **Step 5: Add `PUT /api/mystic`**

In `create_admin_app()` add a PUT handler that parses an object, calls `save_mystic_config()`, converts `ValueError` to a 400 JSON error with the exact validation message, and returns `{"ok": True, "mystic": payload}`.

Register the PUT route before the unknown API route and update the route-order tests.

- [ ] **Step 6: Apply configuration to the new services**

Change `AdminManager.apply_config()` to call:

```python
domain.apply_admin_config(config)
beast_realm.apply_admin_config(config)
mystic_dungeon.apply_admin_config(config)
```

Do not keep old mystic globals in `domain.py`.

- [ ] **Step 7: Run admin tests**

Run:

```powershell
uv run pytest tests/test_admin_routes.py tests/test_mystic_dungeon.py -q
```

Expected: PASS for defaults, validation errors, GET/PUT routes, and service config application.

---

### Task 14: Build The Editable Mystic Web Workspace

**Files:**
- Modify: `webui/src/lib/types.ts`
- Modify: `webui/src/lib/api.ts`
- Modify: `webui/src/lib/api.test.ts`
- Modify: `webui/src/features/mystic/mystic-workspace.tsx`
- Create: `webui/src/features/mystic/mystic-workspace.test.tsx`
- Modify: `webui/src/App.tsx`

- [ ] **Step 1: Write failing API and workspace tests**

Add an API test asserting:

```typescript
it("saves mystic configuration through the focused endpoint", async () => {
  mockFetchJson({ ok: true, mystic: mysticPayload.mystic })
  await saveMysticConfig(mysticPayload.mystic)
  expect(fetch).toHaveBeenCalledWith(expect.stringContaining("/api/mystic"), expect.objectContaining({ method: "PUT" }))
})
```

Create `mystic-workspace.test.tsx`:

```tsx
it("edits map tiers, encounter timing, and saves a structured payload", async () => {
  const onSave = vi.fn()
  render(<MysticWorkspace payload={payload} onSave={onSave} />)

  expect(screen.getByRole("heading", { name: "秘境规则" })).toBeInTheDocument()
  expect(screen.getByText("24 格")).toBeInTheDocument()
  fireEvent.change(screen.getByLabelText("普通遭遇应战时间"), { target: { value: "45" } })
  fireEvent.click(screen.getByRole("button", { name: "保存秘境配置" }))

  expect(onSave).toHaveBeenCalledWith(expect.objectContaining({ encounter_response_seconds: 45 }))
})
```

- [ ] **Step 2: Run frontend tests and confirm the editable API is missing**

Run:

```powershell
Set-Location webui
pnpm run test -- src/lib/api.test.ts src/features/mystic/mystic-workspace.test.tsx
Set-Location ..
```

Expected: FAIL because `saveMysticConfig` and editable props do not exist.

- [ ] **Step 3: Add structured TypeScript types**

```typescript
export type MysticMapSizeRule = {
  minimum_boss_realm_index: number
  node_count: 24 | 28 | 32 | 36 | 40 | 44 | 48
}

export type MysticConfig = {
  enabled_types: string[]
  enabled_high_risk_types: string[]
  map_size_rules: MysticMapSizeRule[]
  min_map_size: MysticMapSizeRule["node_count"]
  max_map_size: MysticMapSizeRule["node_count"]
  normal_node_weights: Record<string, number>
  high_risk_node_weights: Record<string, number>
  normal_branch_density: number
  high_risk_branch_density: number
  high_risk_loop_count: number
  consecutive_combat_limit: number
  ordinary_monster_hp_multiplier: number
  boss_hp_multiplier: number
  reward_multiplier: number
  damage_growth_per_ten_rounds: number
  encounter_response_seconds: number
  battle_prepare_seconds: number
  player_action_seconds: number
  boss_vote_seconds: number
  leader_inactive_seconds: number
  leader_transfer_vote_seconds: number
  rescue_wait_seconds: number
  signin_normal_token_count: number
  signin_high_risk_token_count: number
  daily_task_normal_token_count: number
  daily_task_high_risk_token_count: number
  background_bindings: Record<string, boolean>
}
```

`MysticPayload.mystic` extends this config with read-only `types`, `high_risk_types`, `supported_map_sizes`, `categories`, `tiers`, and `grades`.

- [ ] **Step 4: Add the focused save function**

```typescript
export function saveMysticConfig(config: MysticConfig) {
  return apiJson(api.put("mystic", { json: config }).json<MysticPayload>())
}
```

- [ ] **Step 5: Replace the read-only workspace with compact editable controls**

`MysticWorkspace` receives:

```typescript
{
  payload: MysticPayload
  onSave: (config: MysticConfig) => void
}
```

Use Ant Design component APIs, not custom colors or typography overrides:

- `Tabs` for map/node/combat/timeouts/assets.
- `Select` for each supported map-size rule.
- `InputNumber` for realm thresholds, loop count, combat limit, multipliers, token counts, and timeouts.
- `Slider` for probability weights and branch density.
- `Checkbox.Group` for enabled normal/high-risk themes.
- A `SaveOutlined` button named `保存秘境配置` with `Modal.confirm` or the existing `ConfirmAction` before save.
- `Tag` status for each background binding.

Keep `className` usage limited to existing layout classes. Do not add custom color/typography CSS.

- [ ] **Step 6: Wire save/mutate in `App.tsx`**

Give `MysticPage` an Ant Design message context and call `saveMysticConfig()`; on success show `秘境配置已保存` and mutate the SWR payload.

- [ ] **Step 7: Run frontend tests, typecheck, lint, and build**

Run:

```powershell
Set-Location webui
pnpm run test -- src/lib/api.test.ts src/features/mystic/mystic-workspace.test.tsx
pnpm run typecheck
pnpm run lint
pnpm run build
Set-Location ..
```

Expected: tests, TypeScript, Biome check, and production build all PASS. Do not run a formatter in write mode.

---

### Task 15: Generate And Publish All 26 GPT Image Backgrounds

**Files:**
- Create: `tools/generate_mystic_map_backgrounds_gpt.py`
- Create: `assets/mystic_maps/backgrounds/*.png`
- Modify: `assets/mystic_maps/manifest.json`
- Modify: `pyproject.toml`
- Modify: `tests/test_mystic_cards.py`

- [ ] **Step 1: Implement prompt generation without hard-coded secrets**

The script reads `OPENAI_API_KEY` from the environment and calls the official image endpoint with model `gpt-image-2`. Use the existing `httpx` runtime dependency and catch `httpx.HTTPError`, `KeyError`, `ValueError`, `OSError`, and image decoding errors explicitly.

Prompt template:

```text
Chinese xianxia game dungeon map background for {display_name}, cinematic high-angle
environmental concept art, wide 16:9 composition, one continuous explorable landscape,
clear visual landmarks distributed across the whole frame, enough readable terrain to
place up to 48 small irregular route nodes, central and edge areas both usable, {theme_details}.
Background plate only: no route lines, no nodes, no arrows, no UI, no text, no letters,
no characters, no monsters, no watermark, no frame, no vignette, no blur.
```

Theme details must come from a complete dictionary keyed by the 26 manifest ids; do not reuse one generic description for all themes.

- [ ] **Step 2: Save source and published outputs separately**

- Save raw API responses and prompts under ignored `ui-sprite-runs/2026-07-16-mystic-backgrounds/{theme_id}/`.
- Decode the generated source image, center-crop/extend to 16:9 without stretching, upscale with Lanczos, and save the published plate to `assets/mystic_maps/backgrounds/{theme_id}.png` at 3840x2160.
- Preserve a manifest SHA-256 for each published file.

- [ ] **Step 3: Generate the images**

Run only after the user approves network image generation and confirms the API key is available:

```powershell
uv run python tools/generate_mystic_map_backgrounds_gpt.py --all
```

Expected: 26 published PNGs and 26 manifest hashes. If tenant policy or the official endpoint blocks generation, stop and ask the user for generated image URLs/files; do not retry third-party endpoints or bypass policy.

- [ ] **Step 4: Add asset validation tests**

```python
def test_every_manifest_theme_has_a_3840_by_2160_background() -> None:
    catalog = MysticTemplateCatalog.from_files()
    assert len(catalog.themes) == 26
    for theme in catalog.themes.values():
        with Image.open(theme.background_path) as image:
            assert image.size == (3840, 2160)
            assert image.mode in {"RGB", "RGBA"}


def test_backgrounds_are_not_blank_or_duplicate() -> None:
    hashes = [sha256(theme.background_path.read_bytes()).hexdigest() for theme in catalog.themes.values()]
    assert len(set(hashes)) == 26
```

- [ ] **Step 5: Package the runtime resources**

Add to `pyproject.toml` package data:

```toml
"assets/mystic_maps/manifest.json",
"assets/mystic_maps/templates.json",
"assets/mystic_maps/backgrounds/*.png",
"assets/mystic_dungeon_ui/*.png",
```

- [ ] **Step 6: Render representative visual checks**

Render normal/high-risk 24/48 node maps for solo, 2-player, and 3-player states. Inspect all six PNGs with the local image viewer for full node visibility, crop quality, route readability, icon sizing, BOSS label placement, and text overlap.

- [ ] **Step 7: Run asset and renderer tests**

Run:

```powershell
uv run pytest tests/test_mystic_cards.py -q
```

Expected: PASS for 26 unique backgrounds, dimensions, package paths, and representative map rendering.

---

### Task 16: Full Regression, Runtime Smoke Test, And Handoff

**Files:**
- Modify only if failures are within approved scope: files listed in this plan
- Generated build output: `assets/admin_web/`

- [ ] **Step 1: Run Python lint and type checks**

Run:

```powershell
uv run ruff check .
uv run mypy
```

Expected: both commands PASS. Do not run `ruff format`.

- [ ] **Step 2: Run focused tests**

Run:

```powershell
uv run pytest tests/test_combat_turns.py tests/test_mystic_dungeon.py tests/test_mystic_storage.py tests/test_mystic_battle.py tests/test_mystic_cards.py tests/test_mystic_integration.py tests/test_admin_routes.py -q
```

Expected: PASS.

- [ ] **Step 3: Run the complete Python test suite**

Run:

```powershell
uv run pytest -q
```

Expected: PASS with no legacy mystic tests remaining.

- [ ] **Step 4: Run the complete frontend gate**

Run:

```powershell
Set-Location webui
pnpm run test
pnpm run typecheck
pnpm run lint
pnpm run build
Set-Location ..
```

Expected: all commands PASS and `assets/admin_web/` is rebuilt.

- [ ] **Step 5: Run legacy and packaging scans**

Run:

```powershell
rg -n "MYSTIC_REALM_MAX_STEPS|record\.mystic_realm|last_failed_mystic_realm|探索 编号|十次探索" __init__.py domain.py storage.py tests
git diff --check
git status --short
```

Expected: no legacy runtime references, no whitespace errors, and only approved files changed. Existing raw player JSON may still contain ignored old keys; runtime code must not read them.

- [ ] **Step 6: Start the Web development server**

Run:

```powershell
Set-Location webui
pnpm run dev -- --host 127.0.0.1 --port 5173
```

If port 5173 is occupied, select the next free port. Keep the server running and provide the local URL.

- [ ] **Step 7: Perform browser and gameplay smoke checks**

In the Web UI:

- Load `/mystic`, edit one map tier and timeout, save, reload, and confirm persistence.
- Verify validation errors appear for unsupported node sizes or invalid probability sums.
- Check desktop and mobile widths for control overlap and label truncation.

In a test group/private session:

- Start one solo and one 2-player dungeon.
- Roll into a branch and resume remaining movement.
- Complete a shared ordinary encounter with one and then two responders.
- Defeat the first response batch and hand off remaining monster HP.
- Reach a 2-player Boss, fail one segment, pass unanimous continuation, and assist it.
- Restart the Bot during movement and during battle, then verify state and private routes recover.

- [ ] **Step 8: Report results without committing**

Summarize changed files, tests, lint/typecheck/build results, preview images, local Web URL, and any remaining risks. Do not stage, commit, push, or create a PR unless the user explicitly requests it.
