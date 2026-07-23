from __future__ import annotations

import asyncio
import importlib
import json
import sys
import types
from datetime import datetime, timedelta
from pathlib import Path


PACKAGE_NAME = "mystic_integration_test_package"
PACKAGE_ROOT = Path(__file__).resolve().parents[1]
if PACKAGE_NAME not in sys.modules:
    package = types.ModuleType(PACKAGE_NAME)
    package.__path__ = [str(PACKAGE_ROOT)]  # type: ignore[attr-defined]
    package.__package__ = PACKAGE_NAME
    sys.modules[PACKAGE_NAME] = package

domain = importlib.import_module(f"{PACKAGE_NAME}.domain")
mystic = importlib.import_module(f"{PACKAGE_NAME}.mystic_dungeon")
battle = importlib.import_module(f"{PACKAGE_NAME}.mystic_battle")
cards = importlib.import_module(f"{PACKAGE_NAME}.mystic_cards")
storage = importlib.import_module(f"{PACKAGE_NAME}.storage")
runtime = importlib.import_module(f"{PACKAGE_NAME}.mystic_runtime")

UserRecord = domain.UserRecord
DungeonPhase = mystic.DungeonPhase
MysticDungeonService = mystic.MysticDungeonService
MysticTemplateCatalog = mystic.MysticTemplateCatalog
MysticBattleService = battle.MysticBattleService
MysticMapRenderer = cards.MysticMapRenderer
JsonStore = storage.JsonStore
MysticRescueRequest = storage.MysticRescueRequest
MysticCommandCoordinator = runtime.MysticCommandCoordinator
DungeonEntryOffer = runtime.DungeonEntryOffer
MysticGroupAction = runtime.MysticGroupAction
parse_mystic_group_command = runtime.parse_mystic_group_command
parse_mystic_private_command = runtime.parse_mystic_private_command

NOW = datetime(2026, 7, 16, 12, 0, 0)


def _token(name: str = "普通秘境令牌") -> dict[str, object]:
    return {
        "tier": "凡品",
        "grade": "下品",
        "category": "秘境令牌",
        "name": name,
        "description": "用于开启秘境副本",
    }


def _coordinator(
    tmp_path: Path,
    *,
    store: JsonStore | None = None,
    dice_value: int = 1,
) -> MysticCommandCoordinator:
    catalog = MysticTemplateCatalog.from_files()
    active_store = store or JsonStore(tmp_path)
    return MysticCommandCoordinator(
        store=active_store,
        dungeon_service=MysticDungeonService(catalog, now=lambda: NOW),
        battle_service=MysticBattleService(
            mystic.default_mystic_gameplay_config(),
            now=lambda: NOW,
        ),
        renderer=MysticMapRenderer(allow_placeholder_background=True),
        id_factory=lambda group_id, user_id: f"run:{group_id}:{user_id}",
        dice_roller=lambda: dice_value,
    )


def _save_players(store: JsonStore) -> None:
    asyncio.run(
        store.save_user(
            UserRecord(
                user_id="leader",
                realm_index=4,
                rewards=[_token()],
            )
        )
    )
    asyncio.run(store.save_user(UserRecord(user_id="member", realm_index=3)))


def _started_team(tmp_path: Path) -> MysticCommandCoordinator:
    coordinator = _coordinator(tmp_path)
    _save_players(coordinator.store)
    asyncio.run(coordinator.handle_group("100", "leader", "创建秘境队伍 普通"))
    asyncio.run(coordinator.handle_group("100", "member", "加入秘境队伍"))
    asyncio.run(coordinator.handle_group("100", "leader", "秘境准备"))
    asyncio.run(coordinator.handle_group("100", "member", "秘境准备"))
    started = asyncio.run(coordinator.handle_group("100", "leader", "开始秘境"))
    assert started.error == ""
    return coordinator


def _land_on_combat_node(
    coordinator: MysticCommandCoordinator,
) -> str:
    run_id = asyncio.run(coordinator.active_run_id("leader"))
    assert run_id is not None
    run = asyncio.run(coordinator.store.get_mystic_run(run_id))
    assert run is not None
    combat_node_id = next(
        node_id
        for node_id, content in run.node_contents.items()
        if content.kind is mystic.NodeKind.COMBAT
    )

    def updater(item: object) -> object:
        item.current_node_id = combat_node_id
        if combat_node_id not in item.visited_node_ids:
            item.visited_node_ids.append(combat_node_id)
        item.phase = DungeonPhase.RESOLVING_NODE
        return item

    asyncio.run(coordinator.store.update_mystic_run(run_id, run.revision, updater))
    return run_id


def test_group_commands_create_join_ready_start_and_roll(tmp_path: Path) -> None:
    coordinator = _coordinator(tmp_path)
    _save_players(coordinator.store)

    created = asyncio.run(
        coordinator.handle_group("100", "leader", "创建秘境队伍 普通")
    )
    joined = asyncio.run(
        coordinator.handle_group("100", "member", "加入秘境队伍")
    )
    asyncio.run(coordinator.handle_group("100", "leader", "秘境准备"))
    asyncio.run(coordinator.handle_group("100", "member", "秘境准备"))
    started = asyncio.run(
        coordinator.handle_group("100", "leader", "开始秘境")
    )
    moved = asyncio.run(coordinator.handle_group("100", "leader", "投骰"))

    assert created.run is not None
    assert joined.run is not None
    assert started.run is not None
    assert started.run.phase is DungeonPhase.READY_TO_ROLL
    assert started.image_bytes
    assert "当前位置" in started.message
    assert moved.map_required
    assert moved.run is not None
    assert moved.run.phase is not DungeonPhase.RESOLVING_NODE
    assert "掷出 1 点" in moved.message


def test_only_leader_can_roll_or_choose_branch(tmp_path: Path) -> None:
    coordinator = _started_team(tmp_path)

    denied = asyncio.run(coordinator.handle_group("100", "member", "投骰"))

    assert denied.error == "只有队长可以投骰。"


def test_lobby_and_private_route_survive_coordinator_restart(tmp_path: Path) -> None:
    first = _coordinator(tmp_path)
    _save_players(first.store)
    asyncio.run(first.handle_group("100", "leader", "创建秘境队伍 普通"))
    restarted_lobby = _coordinator(tmp_path, store=JsonStore(tmp_path))

    assert asyncio.run(restarted_lobby.active_run_id("leader")) == "run:100:leader"

    asyncio.run(restarted_lobby.handle_group("100", "member", "加入秘境队伍"))
    asyncio.run(restarted_lobby.handle_group("100", "leader", "秘境准备"))
    asyncio.run(restarted_lobby.handle_group("100", "member", "秘境准备"))
    asyncio.run(restarted_lobby.handle_group("100", "leader", "开始秘境"))
    second = _coordinator(tmp_path, store=JsonStore(tmp_path))
    route = asyncio.run(second.resolve_private_context("leader"))

    assert route is not None
    assert route.run_id == "run:100:leader"
    assert route.source_group_id == "100"


def test_team_entry_charges_only_when_started(tmp_path: Path) -> None:
    coordinator = _coordinator(tmp_path)
    _save_players(coordinator.store)
    asyncio.run(coordinator.handle_group("100", "leader", "创建秘境队伍 普通"))

    before = asyncio.run(coordinator.store.get_user("leader"))

    asyncio.run(coordinator.handle_group("100", "member", "加入秘境队伍"))
    asyncio.run(coordinator.handle_group("100", "leader", "秘境准备"))
    asyncio.run(coordinator.handle_group("100", "member", "秘境准备"))
    asyncio.run(coordinator.handle_group("100", "leader", "开始秘境"))
    after = asyncio.run(coordinator.store.get_user("leader"))

    assert domain.reward_count_by_names(before, ["普通秘境令牌"]) == 1
    assert domain.reward_count_by_names(after, ["普通秘境令牌"]) == 0


def test_tianji_offer_creates_new_engine_solo_run_and_private_route(
    tmp_path: Path,
) -> None:
    coordinator = _coordinator(tmp_path)
    _save_players(coordinator.store)
    offer = DungeonEntryOffer(
        mode=mystic.DungeonMode.SOLO,
        risk=mystic.DungeonRisk.NORMAL,
        theme_id="ancient_sect_ruins",
        boss_realm_index=4,
        insight=True,
    )

    result = asyncio.run(coordinator.create_from_offer("100", "leader", offer))
    route = asyncio.run(coordinator.resolve_private_context("leader"))

    assert result.run is not None
    assert result.run.mode is mystic.DungeonMode.SOLO
    assert result.run.theme_id == "ancient_sect_ruins"
    assert route is not None
    assert route.source_group_id == "100"


def test_team_combat_opens_group_response_then_private_preparation(
    tmp_path: Path,
) -> None:
    coordinator = _started_team(tmp_path)
    run_id = _land_on_combat_node(coordinator)

    opened = asyncio.run(coordinator.resolve_current_node(run_id))
    leader_joined = asyncio.run(coordinator.handle_group("100", "leader", "应战"))
    member_joined = asyncio.run(coordinator.handle_group("100", "member", "应战"))
    encounter = asyncio.run(
        coordinator.store.get_mystic_encounter(
            member_joined.run.active_encounter_id if member_joined.run else ""
        )
    )

    assert opened.run is not None
    assert opened.run.phase is DungeonPhase.AWAITING_ENCOUNTER_RESPONSE
    assert leader_joined.private_messages == (("leader", "秘境配装"),)
    assert leader_joined.run is not None
    assert leader_joined.run.phase is DungeonPhase.AWAITING_ENCOUNTER_RESPONSE
    assert member_joined.private_messages == (("member", "秘境配装"),)
    assert member_joined.run is not None
    assert member_joined.run.phase is DungeonPhase.PREPARING_BATTLE
    assert encounter is not None
    assert set(encounter.participants) == {"leader", "member"}

def test_private_confirmation_and_attack_persist_combat_state(
    tmp_path: Path,
) -> None:
    coordinator = _started_team(tmp_path)
    run_id = _land_on_combat_node(coordinator)
    asyncio.run(coordinator.resolve_current_node(run_id))
    asyncio.run(coordinator.handle_group("100", "leader", "应战"))
    asyncio.run(coordinator.handle_group("100", "member", "应战"))

    leader_confirmed = asyncio.run(
        coordinator.handle_private("leader", "确认配装", action_id="confirm:1")
    )
    member_confirmed = asyncio.run(
        coordinator.handle_private("member", "确认配装", action_id="confirm:2")
    )
    attacked = asyncio.run(
        coordinator.handle_private("leader", "普通攻击", action_id="attack:1")
    )
    route = asyncio.run(coordinator.resolve_private_context("leader"))
    assert route is not None
    run = asyncio.run(coordinator.store.get_mystic_run(route.run_id))
    assert run is not None
    encounter = asyncio.run(
        coordinator.store.get_mystic_encounter(run.active_encounter_id or "")
    )

    assert leader_confirmed.run is not None
    assert leader_confirmed.run.phase is DungeonPhase.PREPARING_BATTLE
    assert member_confirmed.run is not None
    assert member_confirmed.run.phase is DungeonPhase.BATTLE_TURN
    assert attacked.message
    assert encounter is not None
    assert "attack:1" in encounter.action_ids
    assert encounter.participants["leader"].valid_action_count == 1
    assert encounter.prepared_user_ids == {"leader", "member"}

def test_external_rescue_uses_private_route_and_pays_only_after_victory(
    tmp_path: Path,
) -> None:
    coordinator = _started_team(tmp_path)
    run_id = _land_on_combat_node(coordinator)
    asyncio.run(coordinator.resolve_current_node(run_id))
    run = asyncio.run(coordinator.store.get_mystic_run(run_id))
    assert run is not None
    encounter = asyncio.run(
        coordinator.store.get_mystic_encounter(run.active_encounter_id or "")
    )
    assert encounter is not None

    def block_run(item: object) -> object:
        item.phase = DungeonPhase.AWAITING_RESCUE
        return item

    blocked = asyncio.run(
        coordinator.store.update_mystic_run(run.run_id, run.revision, block_run)
    )
    leader = asyncio.run(coordinator.store.get_user("leader"))
    leader.spirit_stones = 1_000
    asyncio.run(coordinator.store.save_user(leader))
    asyncio.run(coordinator.store.save_user(UserRecord(user_id="rescuer")))
    request = MysticRescueRequest(
        request_id="rescue-1",
        run_id=blocked.run_id,
        encounter_id=encounter.encounter_id,
        group_id="100",
        requester_id="leader",
        requester_name="Leader",
        reward_stones=600,
        monster_snapshot=encounter.monster_record,
        remaining_hp=1,
        deadline="2026-07-16T12:30:00",
    )
    asyncio.run(coordinator.store.create_rescue_request(request))

    taken = asyncio.run(coordinator.take_rescue("100", "rescue-1", "rescuer"))
    route = asyncio.run(coordinator.resolve_private_context("rescuer"))
    accepted = asyncio.run(
        coordinator.accepts_private_message("rescuer", "确认配装")
    )
    before = asyncio.run(coordinator.store.get_user("rescuer"))
    asyncio.run(
        coordinator.handle_private("rescuer", "确认配装", action_id="rescue:confirm")
    )
    asyncio.run(
        coordinator.handle_private("rescuer", "普通攻击", action_id="rescue:attack")
    )
    after = asyncio.run(coordinator.store.get_user("rescuer"))
    restored = asyncio.run(coordinator.store.get_mystic_run(run_id))

    assert taken.private_messages == (("rescuer", "秘境配装"),)
    assert route is not None
    assert route.rescue_request_id == "rescue-1"
    assert accepted
    assert before.spirit_stones == 0
    assert after.spirit_stones == 600
    assert restored is not None
    assert restored.phase is DungeonPhase.READY_TO_ROLL


def _boss_team(tmp_path: Path) -> tuple[object, object, object]:
    coordinator = _coordinator(tmp_path)
    _save_players(coordinator.store)
    asyncio.run(coordinator.store.save_user(UserRecord(user_id="third", realm_index=3)))
    asyncio.run(coordinator.handle_group("100", "leader", "创建秘境队伍 普通"))
    asyncio.run(coordinator.handle_group("100", "member", "加入秘境队伍"))
    asyncio.run(coordinator.handle_group("100", "third", "加入秘境队伍"))
    for user_id in ("leader", "member", "third"):
        asyncio.run(coordinator.handle_group("100", user_id, "秘境准备"))
    started = asyncio.run(coordinator.handle_group("100", "leader", "开始秘境"))
    assert started.run is not None
    run = started.run

    def land_on_boss(item: object) -> object:
        item.current_node_id = item.boss_node_id
        if item.boss_node_id not in item.visited_node_ids:
            item.visited_node_ids.append(item.boss_node_id)
        item.phase = DungeonPhase.RESOLVING_NODE
        return item

    landed = asyncio.run(
        coordinator.store.update_mystic_run(run.run_id, run.revision, land_on_boss)
    )
    result = asyncio.run(coordinator.resolve_current_node(landed.run_id))
    encounter = asyncio.run(
        coordinator.store.get_mystic_encounter(
            result.run.active_encounter_id if result.run else ""
        )
    )
    assert result.run is not None
    assert encounter is not None
    return coordinator, result, encounter


def test_boss_node_privately_prepares_every_fixed_member(
    tmp_path: Path,
) -> None:
    coordinator, result, encounter = _boss_team(tmp_path)

    assert {user_id for user_id, _ in result.private_messages} == {
        "leader",
        "member",
        "third",
    }
    assert encounter is not None
    assert len(encounter.boss_segments) == 3
    segment_hp = {segment.initial_hp for segment in encounter.boss_segments.values()}
    assert len(segment_hp) == 1
    assert encounter.total_initial_hp == next(iter(segment_hp)) * 3
    assert result.run is not None
    model = coordinator._render_model(result.run)
    boss_node = next(node for node in model.nodes if node.kind is mystic.NodeKind.BOSS)
    assert boss_node.boss_portrait_path is not None
    assert boss_node.boss_portrait_path.is_file()
    assert "character_portraits" in boss_node.boss_portrait_path.parts


def test_three_player_majority_continue_preserves_hp_and_allows_assist(
    tmp_path: Path,
) -> None:
    coordinator, opened, encounter = _boss_team(tmp_path)
    run = opened.run
    assert run is not None
    for owner in ("leader", "third"):
        encounter.boss_segments[f"segment:{owner}"].hp = 0
        encounter.boss_segments[f"segment:{owner}"].cleared = True
    encounter.boss_segments["segment:member"].hp = 50
    encounter.participants["member"].state = domain.CombatRuntimeState(
        hp=0,
        max_hp=encounter.participants["member"].state.max_hp,
        mana=encounter.participants["member"].state.mana,
        max_mana=encounter.participants["member"].state.max_mana,
        cooldowns=encounter.participants["member"].state.cooldowns,
    )
    encounter.participants["member"].defeated = True
    encounter.phase = battle.EncounterPhase.ACTIVE
    encounter.phase_deadline = None
    saved_encounter = asyncio.run(
        coordinator.store.update_mystic_encounter(
            encounter.encounter_id,
            encounter.revision,
            lambda _: encounter,
        )
    )

    def activate_run(item: object) -> object:
        item.phase = DungeonPhase.BATTLE_TURN
        return item

    active_run = asyncio.run(
        coordinator.store.update_mystic_run(run.run_id, run.revision, activate_run)
    )
    opened_vote = asyncio.run(coordinator.finish_boss_batch(active_run.run_id))
    first = asyncio.run(
        coordinator.handle_group("100", "leader", "秘境续战 同意")
    )
    second = asyncio.run(
        coordinator.handle_group("100", "third", "秘境续战 同意")
    )
    before_hp = saved_encounter.boss_segments["segment:member"].hp
    asyncio.run(coordinator.handle_group("100", "leader", "应战 member"))
    restored = asyncio.run(
        coordinator.store.get_mystic_encounter(encounter.encounter_id)
    )

    assert opened_vote.vote_created
    assert not first.vote_passed
    assert second.vote_passed
    assert restored is not None
    assert restored.boss_segments["segment:member"].hp == before_hp
    assert restored.participants["leader"].target_segment_id == "segment:member"
    assert restored.phase_deadline is not None
    assert datetime.fromisoformat(restored.phase_deadline) > NOW


def test_boss_victory_settles_every_member_and_completes_run(
    tmp_path: Path,
) -> None:
    coordinator, opened, encounter = _boss_team(tmp_path)
    run = opened.run
    assert run is not None
    for owner in ("member", "third"):
        encounter.boss_segments[f"segment:{owner}"].hp = 0
        encounter.boss_segments[f"segment:{owner}"].cleared = True
    encounter.boss_segments["segment:leader"].hp = 1
    encounter.phase = battle.EncounterPhase.ACTIVE
    asyncio.run(
        coordinator.store.update_mystic_encounter(
            encounter.encounter_id,
            encounter.revision,
            lambda _: encounter,
        )
    )

    def activate_run(item: object) -> object:
        item.phase = DungeonPhase.BATTLE_TURN
        item.temporary_rewards_by_user = {
            user_id: [{"category": "灵石", "name": "灵石", "amount": 10}]
            for user_id in item.member_ids
        }
        return item

    active = asyncio.run(
        coordinator.store.update_mystic_run(run.run_id, run.revision, activate_run)
    )
    asyncio.run(
        coordinator.handle_private(
            "leader",
            "普通攻击",
            action_id="boss:final",
        )
    )
    completed = asyncio.run(coordinator.store.get_mystic_run(active.run_id))

    assert completed is not None
    assert completed.phase is DungeonPhase.COMPLETED
    for user_id in ("leader", "member", "third"):
        record = asyncio.run(coordinator.store.get_user(user_id))
        assert record.spirit_stones == 10


def test_group_command_returns_controlled_error_for_stale_state(
    tmp_path: Path,
) -> None:
    coordinator = _coordinator(tmp_path)

    async def raise_conflict(*args: object, **kwargs: object) -> object:
        raise storage.MysticRunConflict("stale")

    coordinator._dispatch_group = raise_conflict
    result = asyncio.run(
        coordinator.handle_group("100", "leader", "秘境状态")
    )

    assert result.error == "秘境状态已发生变化，请重新发送指令。"


def test_parser_accepts_mystic_commands_without_stealing_unrelated_commands() -> None:
    roll = parse_mystic_group_command(" 投骰 ")
    branch = parse_mystic_group_command("选择分支 2")

    assert roll is not None
    assert roll.action is MysticGroupAction.ROLL
    assert roll.argument == ""
    assert branch is not None
    assert branch.action is MysticGroupAction.CHOOSE_BRANCH
    assert parse_mystic_group_command("普通斗法 张三") is None
    assert parse_mystic_group_command("装备 青锋剑") is None
    assert parse_mystic_private_command("秘境配装 青锋剑") == "秘境配装 青锋剑"
    assert parse_mystic_private_command("装备 青锋剑") is None


def test_restart_expires_response_and_vote_using_original_deadline(
    tmp_path: Path,
) -> None:
    coordinator = _started_team(tmp_path)
    run_id = _land_on_combat_node(coordinator)
    opened = asyncio.run(coordinator.resolve_current_node(run_id))
    run = opened.run
    assert run is not None
    encounter = asyncio.run(
        coordinator.store.get_mystic_encounter(run.active_encounter_id or "")
    )
    assert encounter is not None

    expired_encounter = asyncio.run(
        coordinator.store.update_mystic_encounter(
            encounter.encounter_id,
            encounter.revision,
            lambda item: _set_deadline(item, NOW - timedelta(seconds=1)),
        )
    )
    assert expired_encounter.phase_deadline is not None

    def expired_vote(item: object) -> object:
        item.active_vote = mystic.DungeonVote(
            vote_id=f"{item.run_id}:boss_continue:expired",
            kind=mystic.VoteKind.BOSS_CONTINUE,
            eligible_user_ids=item.member_ids,
            approvals=set(),
            rejections=set(),
            deadline=(NOW - timedelta(seconds=1)).isoformat(),
            prior_phase=DungeonPhase.BATTLE_TURN,
        )
        item.phase = DungeonPhase.AWAITING_BOSS_VOTE
        return item

    voted = asyncio.run(
        coordinator.store.update_mystic_run(run.run_id, run.revision, expired_vote)
    )
    recovered = asyncio.run(coordinator.recover_active_runs())
    closed = asyncio.run(coordinator.store.get_mystic_run(voted.run_id))

    assert recovered.response_expirations == 1
    assert recovered.vote_expirations == 0
    assert recovered.scheduled_deadline_count == 0
    assert closed is not None
    assert closed.phase is DungeonPhase.FAILED


def test_restart_restores_private_routes_and_active_action_deadlines(
    tmp_path: Path,
) -> None:
    first = _started_team(tmp_path)
    run_id = _land_on_combat_node(first)
    opened = asyncio.run(first.resolve_current_node(run_id))
    run = opened.run
    assert run is not None
    encounter = asyncio.run(
        first.store.get_mystic_encounter(run.active_encounter_id or "")
    )
    assert encounter is not None
    assert encounter.phase_deadline is not None

    state = json.loads(first.store.mystic_file_path.read_text(encoding="utf-8"))
    state["private_routes"] = {}
    first.store.mystic_file_path.write_text(
        json.dumps(state, ensure_ascii=False),
        encoding="utf-8",
    )

    restarted = _coordinator(tmp_path, store=JsonStore(tmp_path))
    recovered = asyncio.run(restarted.recover_active_runs())
    route = asyncio.run(restarted.resolve_private_context("leader"))

    assert route is not None
    assert route.run_id == run_id
    assert route.source_group_id == "100"
    assert recovered.scheduled_deadline_count == 1
    assert restarted.scheduled_deadline_count == 1


def _set_deadline(item: object, deadline: datetime) -> object:
    item.phase_deadline = deadline.isoformat()
    return item

def test_same_group_solo_runs_route_by_actor_and_private_status(tmp_path: Path) -> None:
    coordinator = _coordinator(tmp_path)
    asyncio.run(
        coordinator.store.save_user(
            UserRecord(user_id="solo-a", realm_index=4, rewards=[_token()])
        )
    )
    asyncio.run(
        coordinator.store.save_user(
            UserRecord(user_id="solo-b", realm_index=4, rewards=[_token()])
        )
    )

    first = asyncio.run(
        coordinator.handle_group("100", "solo-a", "创建单人秘境 普通")
    )
    second = asyncio.run(
        coordinator.handle_group("100", "solo-b", "创建单人秘境 普通")
    )
    first_status = asyncio.run(
        coordinator.handle_group("100", "solo-a", "秘境状态")
    )
    second_status = asyncio.run(
        coordinator.handle_private("solo-b", "秘境状态", action_id="status-b")
    )

    assert first.run is not None and second.run is not None
    assert first.run.run_id != second.run.run_id
    assert first_status.run is not None
    assert first_status.run.run_id == first.run.run_id
    assert second_status.run is not None
    assert second_status.run.run_id == second.run.run_id


def test_roll_command_does_not_accept_player_selected_value() -> None:
    assert parse_mystic_group_command("投骰") == runtime.MysticParsedCommand(
        MysticGroupAction.ROLL
    )
    assert parse_mystic_group_command("投骰 6") is None

def test_private_auto_battle_finishes_eligible_solo_encounter(tmp_path: Path) -> None:
    coordinator = _coordinator(tmp_path)
    asyncio.run(
        coordinator.store.save_user(
            UserRecord(user_id="solo", realm_index=4, rewards=[_token()])
        )
    )
    created = asyncio.run(
        coordinator.handle_group("100", "solo", "创建单人秘境 普通")
    )
    assert created.run is not None
    run = created.run
    combat_node_id = next(
        node_id
        for node_id, content in run.node_contents.items()
        if content.kind is mystic.NodeKind.COMBAT
    )

    def land_on_combat(item: object) -> object:
        item.current_node_id = combat_node_id
        if combat_node_id not in item.visited_node_ids:
            item.visited_node_ids.append(combat_node_id)
        item.phase = DungeonPhase.RESOLVING_NODE
        return item

    landed = asyncio.run(
        coordinator.store.update_mystic_run(run.run_id, run.revision, land_on_combat)
    )
    opened = asyncio.run(coordinator.resolve_current_node(landed.run_id))
    assert opened.run is not None
    encounter = asyncio.run(
        coordinator.store.get_mystic_encounter(opened.run.active_encounter_id or "")
    )
    assert encounter is not None

    def weaken_monster(item: object) -> object:
        item.monster_record["realm_index"] = 0
        item.shared_monster_hp = 1
        return item

    asyncio.run(
        coordinator.store.update_mystic_encounter(
            encounter.encounter_id,
            encounter.revision,
            weaken_monster,
        )
    )
    asyncio.run(
        coordinator.handle_private("solo", "确认配装", action_id="solo:confirm")
    )
    result = asyncio.run(
        coordinator.handle_private("solo", "自动战斗", action_id="solo:auto")
    )
    restored = asyncio.run(coordinator.store.get_mystic_run(run.run_id))

    assert result.error == ""
    assert restored is not None
    assert restored.phase is DungeonPhase.READY_TO_ROLL
    assert restored.temporary_rewards_by_user["solo"]


def test_ordinary_loot_only_goes_to_members_who_actually_fought(tmp_path: Path) -> None:
    coordinator = _started_team(tmp_path)
    run_id = _land_on_combat_node(coordinator)
    opened = asyncio.run(coordinator.resolve_current_node(run_id))
    assert opened.run is not None
    asyncio.run(coordinator.handle_group("100", "leader", "应战"))
    prepared = asyncio.run(coordinator.handle_group("100", "member", "应战"))
    assert prepared.run is not None
    encounter = asyncio.run(
        coordinator.store.get_mystic_encounter(prepared.run.active_encounter_id or "")
    )
    assert encounter is not None

    def one_hp(item: object) -> object:
        item.shared_monster_hp = 1
        return item

    asyncio.run(
        coordinator.store.update_mystic_encounter(
            encounter.encounter_id,
            encounter.revision,
            one_hp,
        )
    )
    asyncio.run(
        coordinator.handle_private("leader", "确认配装", action_id="loot:confirm:1")
    )
    asyncio.run(
        coordinator.handle_private("member", "确认配装", action_id="loot:confirm:2")
    )
    asyncio.run(
        coordinator.handle_private("leader", "普通攻击", action_id="loot:attack")
    )
    restored = asyncio.run(coordinator.store.get_mystic_run(run_id))

    assert restored is not None
    assert restored.phase is DungeonPhase.READY_TO_ROLL
    assert restored.temporary_rewards_by_user["leader"]
    assert restored.temporary_rewards_by_user["member"] == []

def test_response_deadline_starts_preparation_for_joined_subset(tmp_path: Path) -> None:
    coordinator = _started_team(tmp_path)
    run_id = _land_on_combat_node(coordinator)
    opened = asyncio.run(coordinator.resolve_current_node(run_id))
    assert opened.run is not None
    joined = asyncio.run(coordinator.handle_group("100", "leader", "应战"))
    assert joined.run is not None
    encounter = asyncio.run(
        coordinator.store.get_mystic_encounter(joined.run.active_encounter_id or "")
    )
    assert encounter is not None
    expired = asyncio.run(
        coordinator.store.update_mystic_encounter(
            encounter.encounter_id,
            encounter.revision,
            lambda item: _set_deadline(item, NOW - timedelta(seconds=1)),
        )
    )

    asyncio.run(coordinator.recover_run(joined.run))
    restored_run = asyncio.run(coordinator.store.get_mystic_run(run_id))
    restored_encounter = asyncio.run(
        coordinator.store.get_mystic_encounter(expired.encounter_id)
    )

    assert restored_run is not None
    assert restored_run.phase is DungeonPhase.PREPARING_BATTLE
    assert restored_encounter is not None
    assert restored_encounter.phase is battle.EncounterPhase.PREPARING
    assert set(restored_encounter.participants) == {"leader"}


def test_preparation_deadline_auto_confirms_current_loadouts(tmp_path: Path) -> None:
    coordinator = _started_team(tmp_path)
    run_id = _land_on_combat_node(coordinator)
    asyncio.run(coordinator.resolve_current_node(run_id))
    asyncio.run(coordinator.handle_group("100", "leader", "应战"))
    prepared = asyncio.run(coordinator.handle_group("100", "member", "应战"))
    assert prepared.run is not None
    encounter = asyncio.run(
        coordinator.store.get_mystic_encounter(prepared.run.active_encounter_id or "")
    )
    assert encounter is not None
    asyncio.run(
        coordinator.store.update_mystic_encounter(
            encounter.encounter_id,
            encounter.revision,
            lambda item: _set_deadline(item, NOW - timedelta(seconds=1)),
        )
    )

    asyncio.run(coordinator.recover_run(prepared.run))
    restored_run = asyncio.run(coordinator.store.get_mystic_run(run_id))
    restored_encounter = asyncio.run(
        coordinator.store.get_mystic_encounter(encounter.encounter_id)
    )

    assert restored_run is not None
    assert restored_run.phase is DungeonPhase.BATTLE_TURN
    assert restored_encounter is not None
    assert restored_encounter.phase is battle.EncounterPhase.ACTIVE
    assert restored_encounter.prepared_user_ids == {"leader", "member"}


def test_active_deadline_submits_default_action_and_reschedules(tmp_path: Path) -> None:
    coordinator = _started_team(tmp_path)
    run_id = _land_on_combat_node(coordinator)
    asyncio.run(coordinator.resolve_current_node(run_id))
    asyncio.run(coordinator.handle_group("100", "leader", "应战"))
    asyncio.run(coordinator.handle_group("100", "member", "应战"))
    asyncio.run(
        coordinator.handle_private("leader", "确认配装", action_id="timeout:confirm:1")
    )
    active = asyncio.run(
        coordinator.handle_private("member", "确认配装", action_id="timeout:confirm:2")
    )
    assert active.run is not None
    encounter = asyncio.run(
        coordinator.store.get_mystic_encounter(active.run.active_encounter_id or "")
    )
    assert encounter is not None

    def expire_active(item: object) -> object:
        item.shared_monster_hp = 10**9
        item.phase_deadline = (NOW - timedelta(seconds=1)).isoformat()
        return item

    asyncio.run(
        coordinator.store.update_mystic_encounter(
            encounter.encounter_id,
            encounter.revision,
            expire_active,
        )
    )
    asyncio.run(coordinator.recover_run(active.run))
    restored = asyncio.run(
        coordinator.store.get_mystic_encounter(encounter.encounter_id)
    )

    assert restored is not None
    assert restored.phase is battle.EncounterPhase.ACTIVE
    assert any(action_id.startswith("timeout:") for action_id in restored.action_ids)
    assert restored.phase_deadline is not None
    assert datetime.fromisoformat(restored.phase_deadline) > NOW


def test_new_deadline_replaces_existing_task_for_same_phase(tmp_path: Path) -> None:
    coordinator = _coordinator(tmp_path)

    async def scenario() -> None:
        key = ("run", "encounter:active")
        assert coordinator._schedule_deadline("run", key[1], NOW + timedelta(hours=1))
        first_task = coordinator._deadline_tasks[key]

        assert coordinator._schedule_deadline("run", key[1], NOW + timedelta(hours=2))
        second_task = coordinator._deadline_tasks[key]
        await asyncio.sleep(0)

        assert first_task is not second_task
        assert first_task.cancelled()
        assert coordinator._deadline_tasks[key] is second_task

        second_task.cancel()
        await asyncio.gather(second_task, return_exceptions=True)

    asyncio.run(scenario())


def test_deadline_runner_retries_after_state_conflict(tmp_path: Path) -> None:
    coordinator = _coordinator(tmp_path)
    attempts = 0

    async def get_run(_: str) -> object:
        return object()

    async def recover(_: object) -> object:
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            raise storage.MysticRunConflict("concurrent update")
        return object()

    coordinator.store.get_mystic_run = get_run  # type: ignore[method-assign]
    coordinator.recover_run = recover  # type: ignore[method-assign]

    asyncio.run(
        coordinator._wait_for_deadline(
            "run",
            ("run", "encounter:active"),
            NOW,
        )
    )

    assert attempts == 2
