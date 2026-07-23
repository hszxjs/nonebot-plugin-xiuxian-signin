from __future__ import annotations

import asyncio
import importlib
import sys
import types
from datetime import datetime
from pathlib import Path

import pytest


PACKAGE_NAME = "mystic_battle_test_package"
PACKAGE_ROOT = Path(__file__).resolve().parents[1]
if PACKAGE_NAME not in sys.modules:
    package = types.ModuleType(PACKAGE_NAME)
    package.__path__ = [str(PACKAGE_ROOT)]  # type: ignore[attr-defined]
    package.__package__ = PACKAGE_NAME
    sys.modules[PACKAGE_NAME] = package

domain = importlib.import_module(f"{PACKAGE_NAME}.domain")
mystic = importlib.import_module(f"{PACKAGE_NAME}.mystic_dungeon")
battle = importlib.import_module(f"{PACKAGE_NAME}.mystic_battle")

CombatRuntimeState = domain.CombatRuntimeState
UserRecord = domain.UserRecord
DungeonPhase = mystic.DungeonPhase
EncounterKind = battle.EncounterKind
EncounterPhase = battle.EncounterPhase
DungeonEncounter = battle.DungeonEncounter
MysticBattleService = battle.MysticBattleService

NOW = datetime(2026, 7, 16, 12, 0, 0)


@pytest.fixture
def service() -> MysticBattleService:
    return MysticBattleService(mystic.default_mystic_gameplay_config(), now=lambda: NOW)


def record(user_id: str, *, realm_index: int = 3) -> UserRecord:
    return UserRecord(
        user_id=user_id,
        root=domain.Root("天阶", 4, "极品", 3, "金", 100, ["金"]),
        realm_index=realm_index,
    )


def test_battle_service_reads_latest_config_provider() -> None:
    state = {"config": mystic.default_mystic_gameplay_config()}
    service = MysticBattleService(
        state["config"],
        now=lambda: NOW,
        config_provider=lambda: state["config"],
    )
    configured = state["config"].to_mapping()
    configured["ordinary_monster_hp_multiplier"] = 2.0
    state["config"] = mystic.MysticGameplayConfig.from_mapping(configured)
    monster = record("monster", realm_index=2)

    encounter = service.create_ordinary_encounter(
        encounter_id="dynamic-config",
        run_id="run-dynamic",
        monster_record=monster,
        fixed_member_ids=("a",),
    )

    assert encounter.shared_monster_hp == domain.combat_max_hp(monster) * 2


def ordinary_encounter(
    service: MysticBattleService,
    *,
    monster_hp: int = 1_000_000,
    participants: tuple[str, ...] = ("a", "b"),
) -> DungeonEncounter:
    encounter = service.create_ordinary_encounter(
        encounter_id="ordinary-1",
        run_id="run-1",
        monster_record=record("monster", realm_index=2),
        fixed_member_ids=participants,
    )
    encounter.shared_monster_hp = monster_hp
    for user_id in participants:
        service.join_ordinary_encounter(
            encounter,
            user_id,
            record(user_id),
            equipment_snapshot={"weapon": f"{user_id}-sword"},
        )
    encounter.phase = EncounterPhase.ACTIVE
    return encounter


def test_two_players_damage_one_shared_monster_and_receive_individual_retaliation(
    service: MysticBattleService,
) -> None:
    encounter = ordinary_encounter(service)
    initial_a_hp = encounter.participants["a"].state.hp
    initial_b_hp = encounter.participants["b"].state.hp

    service.submit_action(encounter, "a", "普通攻击", action_id="a:1")
    service.submit_action(encounter, "b", "普通攻击", action_id="b:1")

    assert encounter.shared_monster_hp < 1_000_000
    assert encounter.participants["a"].state.hp < initial_a_hp
    assert encounter.participants["b"].state.hp < initial_b_hp


def test_action_lock_registry_releases_entry_after_action(
    service: MysticBattleService,
) -> None:
    encounter = ordinary_encounter(service, participants=("a",))

    service.submit_action(encounter, "a", "普通攻击", action_id="a:lock")

    assert service._locks == {}


def test_duplicate_action_id_does_not_damage_twice(
    service: MysticBattleService,
) -> None:
    encounter = ordinary_encounter(service, participants=("a",))

    first = service.submit_action(encounter, "a", "普通攻击", action_id="a:1")
    hp_after_first = encounter.shared_monster_hp
    second = service.submit_action(encounter, "a", "普通攻击", action_id="a:1")

    assert second == first
    assert encounter.shared_monster_hp == hp_after_first
    assert encounter.action_ids == {"a:1"}


def test_defeated_participant_still_gets_loot_after_team_victory(
    service: MysticBattleService,
) -> None:
    encounter = ordinary_encounter(service)
    encounter.participants["a"].valid_action_count = 1
    encounter.participants["a"].defeated = True
    encounter.participants["a"].state = CombatRuntimeState(
        hp=0,
        max_hp=encounter.participants["a"].state.max_hp,
        mana=encounter.participants["a"].state.mana,
        max_mana=encounter.participants["a"].state.max_mana,
        cooldowns=encounter.participants["a"].state.cooldowns,
    )
    encounter.participants["b"].valid_action_count = 1
    encounter.shared_monster_hp = 0

    result = service.finish_encounter(encounter)

    assert result.completed
    assert set(result.eligible_loot_user_ids) == {"a", "b"}


def test_ordinary_encounter_requests_rescue_after_every_member_was_attempted(
    service: MysticBattleService,
) -> None:
    encounter = ordinary_encounter(service)
    for participant in encounter.participants.values():
        participant.defeated = True
    encounter.attempted_user_ids = {"a", "b"}

    result = service.finish_encounter(encounter)

    assert not result.completed
    assert result.needs_rescue
    assert encounter.shared_monster_hp > 0


def test_team_boss_has_h_times_n_total_hp_and_h_per_segment(
    service: MysticBattleService,
) -> None:
    encounter = service.create_boss_encounter(base_hp=500_000, member_ids=("a", "b", "c"))

    assert encounter.total_initial_hp == 1_500_000
    assert [segment.initial_hp for segment in encounter.boss_segments.values()] == [500_000] * 3
    assert [segment.hp for segment in encounter.boss_segments.values()] == [500_000] * 3


def test_continue_keeps_hp_and_allows_cleared_member_to_assist(
    service: MysticBattleService,
) -> None:
    encounter = service.create_boss_encounter(base_hp=500_000, member_ids=("a", "b", "c"))
    encounter.boss_segments["segment:a"].hp = 0
    encounter.boss_segments["segment:a"].cleared = True
    encounter.phase = EncounterPhase.AWAITING_CONTINUE_VOTE
    before = encounter.to_dict()

    assert service.open_boss_continuation(
        encounter,
        approvals={"a": True, "b": True, "c": False},
    )
    service.join_boss_assist(encounter, helper_id="a", segment_id="segment:c")

    assert encounter.boss_segments["segment:c"].hp == before["boss_segments"]["segment:c"]["hp"]
    assert encounter.participants["a"].state.hp == before["participants"]["a"]["state"]["hp"]
    assert encounter.participants["a"].target_segment_id == "segment:c"


def test_two_player_boss_continuation_requires_unanimity(
    service: MysticBattleService,
) -> None:
    failed = service.create_boss_encounter(base_hp=100, member_ids=("a", "b"))
    failed.phase = EncounterPhase.AWAITING_CONTINUE_VOTE
    assert not service.open_boss_continuation(failed, approvals={"a": True, "b": False})
    assert failed.phase is EncounterPhase.FAILED

    passed = service.create_boss_encounter(base_hp=100, member_ids=("a", "b"))
    passed.phase = EncounterPhase.AWAITING_CONTINUE_VOTE
    assert service.open_boss_continuation(passed, approvals={"a": True, "b": True})
    assert passed.phase is EncounterPhase.ACTIVE


def test_three_player_boss_continuation_uses_majority(
    service: MysticBattleService,
) -> None:
    encounter = service.create_boss_encounter(base_hp=100, member_ids=("a", "b", "c"))
    encounter.phase = EncounterPhase.AWAITING_CONTINUE_VOTE

    assert service.open_boss_continuation(
        encounter,
        approvals={"a": True, "b": True, "c": False},
    )


def test_all_zero_hp_team_fails_boss_without_continuation(
    service: MysticBattleService,
) -> None:
    encounter = service.create_boss_encounter(base_hp=100, member_ids=("a", "b"))
    encounter.phase = EncounterPhase.AWAITING_CONTINUE_VOTE
    for participant in encounter.participants.values():
        participant.state = CombatRuntimeState(
            hp=0,
            max_hp=participant.state.max_hp,
            mana=participant.state.mana,
            max_mana=participant.state.max_mana,
            cooldowns=participant.state.cooldowns,
        )
        participant.defeated = True

    assert not service.open_boss_continuation(
        encounter,
        approvals={"a": True, "b": True},
    )
    assert encounter.phase is EncounterPhase.FAILED


def test_zero_hp_helper_is_rejected_and_multiple_living_helpers_can_share_segment(
    service: MysticBattleService,
) -> None:
    encounter = service.create_boss_encounter(base_hp=100, member_ids=("a", "b", "c"))
    for owner in ("a", "b"):
        encounter.boss_segments[f"segment:{owner}"].hp = 0
        encounter.boss_segments[f"segment:{owner}"].cleared = True
    encounter.phase = EncounterPhase.ACTIVE
    encounter.participants["a"].state = CombatRuntimeState(
        hp=0,
        max_hp=encounter.participants["a"].state.max_hp,
        mana=encounter.participants["a"].state.mana,
        max_mana=encounter.participants["a"].state.max_mana,
        cooldowns={},
    )

    with pytest.raises(ValueError, match="zero HP"):
        service.join_boss_assist(encounter, helper_id="a", segment_id="segment:c")
    service.join_boss_assist(encounter, helper_id="b", segment_id="segment:c")
    encounter.participants["a"].state = CombatRuntimeState(
        hp=1,
        max_hp=encounter.participants["a"].state.max_hp,
        mana=encounter.participants["a"].state.mana,
        max_mana=encounter.participants["a"].state.max_mana,
        cooldowns={},
    )
    service.join_boss_assist(encounter, helper_id="a", segment_id="segment:c")

    assert encounter.participants["a"].target_segment_id == "segment:c"
    assert encounter.participants["b"].target_segment_id == "segment:c"


def test_auto_battle_requires_strictly_higher_realm(
    service: MysticBattleService,
) -> None:
    encounter = ordinary_encounter(service, participants=("a",))
    encounter.monster_record["realm_index"] = 3

    with pytest.raises(ValueError, match="strictly higher"):
        service.set_auto_battle(encounter, "a", record("a", realm_index=3))
    service.set_auto_battle(encounter, "a", record("a", realm_index=4))

    assert encounter.participants["a"].auto_battle


def test_timed_out_action_uses_normal_serialized_action_path(
    service: MysticBattleService,
) -> None:
    encounter = ordinary_encounter(service, participants=("a",))

    result = service.resolve_timed_out_action(encounter, "a", action_id="timeout:a:1")

    assert result["action_id"] == "timeout:a:1"
    assert encounter.action_ids == {"timeout:a:1"}
    assert encounter.participants["a"].valid_action_count == 1


def test_auto_actions_persist_each_turn_and_yield(
    service: MysticBattleService,
) -> None:
    encounter = ordinary_encounter(service, monster_hp=1, participants=("a",))
    service.set_auto_battle(encounter, "a", record("a", realm_index=4))
    revisions: list[int] = []

    async def persist(item: DungeonEncounter) -> None:
        revisions.append(item.revision)

    asyncio.run(service.run_auto_actions(encounter, "a", persist=persist, max_actions=3))

    assert revisions
    assert encounter.phase is EncounterPhase.COMPLETED


def test_encounter_round_trips_explicit_combat_state(
    service: MysticBattleService,
) -> None:
    encounter = ordinary_encounter(service, participants=("a",))
    service.submit_action(encounter, "a", "普通攻击", action_id="a:1")

    restored = DungeonEncounter.from_dict(encounter.to_dict())

    assert restored == encounter
    assert restored.action_ids == {"a:1"}
    assert restored.participants["a"].state.turn == encounter.participants["a"].state.turn
