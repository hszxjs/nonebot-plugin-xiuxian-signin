from __future__ import annotations

import asyncio
import importlib
import json
import sys
import types
from datetime import datetime
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Iterator

import pytest


PACKAGE_NAME = "mystic_storage_test_package"
PACKAGE_ROOT = Path(__file__).resolve().parents[1]
if PACKAGE_NAME not in sys.modules:
    package = types.ModuleType(PACKAGE_NAME)
    package.__path__ = [str(PACKAGE_ROOT)]  # type: ignore[attr-defined]
    package.__package__ = PACKAGE_NAME
    sys.modules[PACKAGE_NAME] = package

domain = importlib.import_module(f"{PACKAGE_NAME}.domain")
mystic = importlib.import_module(f"{PACKAGE_NAME}.mystic_dungeon")
battle = importlib.import_module(f"{PACKAGE_NAME}.mystic_battle")
storage = importlib.import_module(f"{PACKAGE_NAME}.storage")

JsonStore = storage.JsonStore
MysticEncounterConflict = storage.MysticEncounterConflict
MysticRescueRequest = storage.MysticRescueRequest
MysticRunConflict = storage.MysticRunConflict
MysticStateCorrupt = storage.MysticStateCorrupt
MysticSettlement = storage.MysticSettlement
DungeonPhase = mystic.DungeonPhase
DungeonRisk = mystic.DungeonRisk
MysticDungeonRun = mystic.MysticDungeonRun
MysticDungeonService = mystic.MysticDungeonService
MysticTemplateCatalog = mystic.MysticTemplateCatalog
MysticBattleService = battle.MysticBattleService
UserRecord = domain.UserRecord

NOW = datetime(2026, 7, 16, 12, 0, 0)
NORMAL_TOKEN = "普通秘境令牌"


@pytest.fixture
def data_dir() -> Iterator[Path]:
    with TemporaryDirectory() as temp_dir:
        yield Path(temp_dir)


@pytest.fixture(scope="module")
def catalog() -> MysticTemplateCatalog:
    return MysticTemplateCatalog.from_files()


def token_reward(name: str = NORMAL_TOKEN) -> dict[str, object]:
    return {
        "tier": "凡品",
        "grade": "下品",
        "category": "秘境令牌",
        "name": name,
        "description": "用于开启秘境副本",
    }


def reward_count(record: UserRecord, name: str) -> int:
    return domain.reward_count_by_names(record, [name])


def started_team_run(
    catalog: MysticTemplateCatalog,
    *,
    run_id: str = "run-1",
    member_count: int = 2,
) -> MysticDungeonRun:
    service = MysticDungeonService(catalog, now=lambda: NOW)
    run = service.create_lobby(run_id, "100", "leader", DungeonRisk.NORMAL)
    for index in range(2, member_count + 1):
        service.join_lobby(run, f"member-{index}")
    for user_id in run.member_ids:
        service.set_ready(run, user_id, True)
    service.start_run(run, boss_realm_index=4, map_seed=7, content_seed=11)
    run.revision = 0
    return run


def save_users_with_tokens(store: JsonStore, *, member_has_token: bool = True) -> None:
    leader = UserRecord(user_id="leader", rewards=[token_reward()])
    member_rewards = [token_reward()] if member_has_token else []
    member = UserRecord(user_id="member-2", rewards=member_rewards)
    asyncio.run(store.save_user(leader))
    asyncio.run(store.save_user(member))


def test_user_record_normalizes_mystic_settlement_ids() -> None:
    raw_ids = ["duplicate", *[f"settlement-{index}" for index in range(105)], "duplicate"]

    record = UserRecord.from_dict(
        {
            "user_id": "42",
            "active_mystic_run_id": "run-42",
            "mystic_settlement_ids": raw_ids,
        }
    )

    assert record.active_mystic_run_id == "run-42"
    assert len(record.mystic_settlement_ids) == 100
    assert len(set(record.mystic_settlement_ids)) == 100
    assert record.to_dict()["mystic_settlement_ids"] == record.mystic_settlement_ids


def test_create_team_run_charges_only_leader_and_indexes_every_member(
    data_dir: Path,
    catalog: MysticTemplateCatalog,
) -> None:
    store = JsonStore(data_dir)
    save_users_with_tokens(store)
    run = started_team_run(catalog)

    saved = asyncio.run(store.create_mystic_run(run, payer_id="leader", token_name=NORMAL_TOKEN))

    assert saved.phase is DungeonPhase.READY_TO_ROLL
    assert asyncio.run(store.find_active_mystic_run_id("leader")) == "run-1"
    assert asyncio.run(store.find_active_mystic_run_id("member-2")) == "run-1"
    leader = asyncio.run(store.get_user("leader"))
    member = asyncio.run(store.get_user("member-2"))
    assert reward_count(leader, NORMAL_TOKEN) == 0
    assert reward_count(member, NORMAL_TOKEN) == 1
    assert leader.active_mystic_run_id == "run-1"
    assert member.active_mystic_run_id == "run-1"
    assert leader.mystic_settlement_ids == ["entry:run-1"]
    assert member.mystic_settlement_ids == []


def test_create_run_without_token_leaves_no_active_state(
    data_dir: Path,
    catalog: MysticTemplateCatalog,
) -> None:
    store = JsonStore(data_dir)
    asyncio.run(store.save_user(UserRecord(user_id="leader")))
    asyncio.run(store.save_user(UserRecord(user_id="member-2")))
    run = started_team_run(catalog)

    with pytest.raises(ValueError, match="token"):
        asyncio.run(store.create_mystic_run(run, payer_id="leader", token_name=NORMAL_TOKEN))

    assert asyncio.run(store.get_mystic_run("run-1")) is None
    assert asyncio.run(store.find_active_mystic_run_id("leader")) is None


def test_compare_and_swap_rejects_stale_run_revision(
    data_dir: Path,
    catalog: MysticTemplateCatalog,
) -> None:
    store = JsonStore(data_dir)
    save_users_with_tokens(store)
    run = started_team_run(catalog)
    asyncio.run(store.create_mystic_run(run, payer_id="leader", token_name=NORMAL_TOKEN))

    first = asyncio.run(store.update_mystic_run(run.run_id, 0, lambda item: item))

    with pytest.raises(MysticRunConflict):
        asyncio.run(store.update_mystic_run(run.run_id, 0, lambda item: item))
    assert first.revision == 1


def test_create_encounter_and_update_run_is_atomic(
    data_dir: Path,
    catalog: MysticTemplateCatalog,
) -> None:
    store = JsonStore(data_dir)
    save_users_with_tokens(store)
    run = started_team_run(catalog)
    saved_run = asyncio.run(
        store.create_mystic_run(run, payer_id="leader", token_name=NORMAL_TOKEN)
    )
    battle_service = MysticBattleService(
        mystic.default_mystic_gameplay_config(),
        now=lambda: NOW,
    )
    encounter = battle_service.create_ordinary_encounter(
        "encounter-1",
        saved_run.run_id,
        UserRecord(user_id="monster"),
        saved_run.member_ids,
    )

    def bind_encounter(item: MysticDungeonRun) -> MysticDungeonRun:
        item.active_encounter_id = encounter.encounter_id
        item.phase = DungeonPhase.AWAITING_ENCOUNTER_RESPONSE
        return item

    updated_run, saved_encounter = asyncio.run(
        store.create_mystic_encounter_and_update_run(
            saved_run.run_id,
            saved_run.revision,
            encounter,
            bind_encounter,
        )
    )

    assert updated_run.active_encounter_id == saved_encounter.encounter_id
    assert updated_run.phase is DungeonPhase.AWAITING_ENCOUNTER_RESPONSE
    stale_encounter = battle_service.create_ordinary_encounter(
        "encounter-stale",
        saved_run.run_id,
        UserRecord(user_id="monster-stale"),
        saved_run.member_ids,
    )
    with pytest.raises(MysticRunConflict):
        asyncio.run(
            store.create_mystic_encounter_and_update_run(
                saved_run.run_id,
                saved_run.revision,
                stale_encounter,
                bind_encounter,
            )
        )
    assert asyncio.run(store.get_mystic_encounter("encounter-stale")) is None


def test_run_and_encounter_compare_and_swap_is_atomic(
    data_dir: Path,
    catalog: MysticTemplateCatalog,
) -> None:
    store = JsonStore(data_dir)
    save_users_with_tokens(store)
    run = started_team_run(catalog)
    saved_run = asyncio.run(
        store.create_mystic_run(run, payer_id="leader", token_name=NORMAL_TOKEN)
    )
    battle_service = MysticBattleService(
        mystic.default_mystic_gameplay_config(),
        now=lambda: NOW,
    )
    encounter = battle_service.create_ordinary_encounter(
        "encounter-atomic",
        saved_run.run_id,
        UserRecord(user_id="monster"),
        saved_run.member_ids,
    )

    def bind_encounter(item: MysticDungeonRun) -> MysticDungeonRun:
        item.active_encounter_id = encounter.encounter_id
        item.phase = DungeonPhase.AWAITING_ENCOUNTER_RESPONSE
        return item

    bound_run, bound_encounter = asyncio.run(
        store.create_mystic_encounter_and_update_run(
            saved_run.run_id,
            saved_run.revision,
            encounter,
            bind_encounter,
        )
    )

    def prepare_run(item: MysticDungeonRun) -> MysticDungeonRun:
        item.phase = DungeonPhase.PREPARING_BATTLE
        return item

    def prepare_encounter(item: object) -> object:
        item.phase = battle.EncounterPhase.PREPARING
        return item

    prepared_run, prepared_encounter = asyncio.run(
        store.update_mystic_run_and_encounter(
            bound_run.run_id,
            bound_run.revision,
            bound_encounter.encounter_id,
            bound_encounter.revision,
            prepare_run,
            prepare_encounter,
        )
    )
    assert prepared_run.phase is DungeonPhase.PREPARING_BATTLE
    assert prepared_encounter.phase is battle.EncounterPhase.PREPARING

    with pytest.raises(MysticRunConflict):
        asyncio.run(
            store.update_mystic_run_and_encounter(
                prepared_run.run_id,
                bound_run.revision,
                prepared_encounter.encounter_id,
                prepared_encounter.revision,
                lambda item: item,
                lambda item: item,
            )
        )
    assert asyncio.run(store.get_mystic_encounter(prepared_encounter.encounter_id)) == prepared_encounter


def test_restart_reloads_active_run(
    data_dir: Path,
    catalog: MysticTemplateCatalog,
) -> None:
    first_store = JsonStore(data_dir)
    save_users_with_tokens(first_store)
    run = started_team_run(catalog)
    asyncio.run(first_store.create_mystic_run(run, payer_id="leader", token_name=NORMAL_TOKEN))

    restarted_store = JsonStore(data_dir)
    restored = asyncio.run(restarted_store.get_mystic_run(run.run_id))

    assert restored == run
    assert [item.run_id for item in asyncio.run(restarted_store.list_active_mystic_runs())] == ["run-1"]


def test_private_route_lookup_persists_across_restart(
    data_dir: Path,
    catalog: MysticTemplateCatalog,
) -> None:
    store = JsonStore(data_dir)
    save_users_with_tokens(store)
    run = started_team_run(catalog)
    saved = asyncio.run(store.create_mystic_run(run, payer_id="leader", token_name=NORMAL_TOKEN))
    asyncio.run(store.bind_mystic_private_routes(saved))

    restarted_store = JsonStore(data_dir)

    assert asyncio.run(restarted_store.resolve_mystic_private_route("member-2")) == ("run-1", "100")


def test_legacy_rescue_file_without_schema_is_treated_as_empty(
    data_dir: Path,
) -> None:
    store = JsonStore(data_dir)
    store.rescue_file_path.write_text(
        json.dumps({"100": {"legacy": {"status": "open"}}}),
        encoding="utf-8",
    )

    assert asyncio.run(store.list_rescue_requests("100")) == []


def test_corrupt_mystic_json_raises_controlled_error(data_dir: Path) -> None:
    store = JsonStore(data_dir)
    store.mystic_file_path.write_text("{broken", encoding="utf-8")

    with pytest.raises(MysticStateCorrupt, match="mystic"):
        asyncio.run(store.list_active_mystic_runs())


def test_close_run_cleans_indexes_routes_and_player_fields(
    data_dir: Path,
    catalog: MysticTemplateCatalog,
) -> None:
    store = JsonStore(data_dir)
    save_users_with_tokens(store)
    run = started_team_run(catalog)
    saved = asyncio.run(store.create_mystic_run(run, payer_id="leader", token_name=NORMAL_TOKEN))
    asyncio.run(store.bind_mystic_private_routes(saved))

    closed = asyncio.run(store.close_mystic_run(run.run_id, DungeonPhase.FAILED))

    assert closed.phase is DungeonPhase.FAILED
    assert asyncio.run(store.find_active_mystic_run_id("leader")) is None
    assert asyncio.run(store.resolve_mystic_private_route("member-2")) is None
    assert asyncio.run(store.get_user("leader")).active_mystic_run_id is None
    assert asyncio.run(store.get_user("member-2")).active_mystic_run_id is None


def test_reward_settlement_is_idempotent_and_cleans_active_state(
    data_dir: Path,
    catalog: MysticTemplateCatalog,
) -> None:
    store = JsonStore(data_dir)
    save_users_with_tokens(store)
    run = started_team_run(catalog)
    saved = asyncio.run(store.create_mystic_run(run, payer_id="leader", token_name=NORMAL_TOKEN))
    asyncio.run(store.bind_mystic_private_routes(saved))
    settlement = MysticSettlement(
        settlement_id="mystic:run-1:complete",
        rewards_by_user={
            "leader": [
                {"category": "灵石", "name": "灵石", "amount": 100},
                {"category": "修为", "name": "修为", "amount": 10},
                {"category": "垂钓次数", "name": "垂钓次数", "amount": 2},
                token_reward("结算测试物品"),
            ]
        },
    )

    first = asyncio.run(store.settle_mystic_run(run.run_id, settlement))
    second = asyncio.run(store.settle_mystic_run(run.run_id, settlement))

    record = asyncio.run(store.get_user("leader"))
    assert first.phase is DungeonPhase.COMPLETED
    assert second == first
    assert record.spirit_stones == 100
    assert record.total_exp == 10
    assert record.realm_exp == 10
    assert record.fishing_chances == 2
    assert reward_count(record, "结算测试物品") == 1
    assert record.mystic_settlement_ids == ["entry:run-1", "mystic:run-1:complete"]
    assert record.active_mystic_run_id is None
    assert asyncio.run(store.find_active_mystic_run_id("leader")) is None
    assert asyncio.run(store.resolve_mystic_private_route("leader")) is None


@pytest.mark.parametrize("charged", [False, True])
def test_restart_recovers_or_discards_creating_runs(
    data_dir: Path,
    catalog: MysticTemplateCatalog,
    charged: bool,
) -> None:
    store = JsonStore(data_dir)
    run = started_team_run(catalog)
    creating_payload = run.to_dict()
    creating_payload["phase"] = DungeonPhase.CREATING.value
    state = {
        "schema_version": 1,
        "runs": {run.run_id: creating_payload},
        "encounters": {},
        "active_by_user": {},
        "private_routes": {},
    }
    store.mystic_file_path.parent.mkdir(parents=True, exist_ok=True)
    store.mystic_file_path.write_text(json.dumps(state, ensure_ascii=False), encoding="utf-8")
    leader_ids = ["entry:run-1"] if charged else []
    users = {
        "leader": UserRecord(
            user_id="leader",
            mystic_settlement_ids=leader_ids,
        ).to_dict(),
        "member-2": UserRecord(user_id="member-2").to_dict(),
    }
    store.user_file_path.write_text(json.dumps(users, ensure_ascii=False), encoding="utf-8")

    active = asyncio.run(store.list_active_mystic_runs())

    if charged:
        assert [item.run_id for item in active] == ["run-1"]
        assert active[0].phase is DungeonPhase.READY_TO_ROLL
        assert asyncio.run(store.find_active_mystic_run_id("member-2")) == "run-1"
    else:
        assert active == []
        assert asyncio.run(store.get_mystic_run("run-1")) is None


def test_encounter_round_trip_survives_restart(data_dir: Path) -> None:
    service = MysticBattleService(mystic.default_mystic_gameplay_config(), now=lambda: NOW)
    encounter = service.create_boss_encounter(base_hp=500, member_ids=("a", "b"))
    encounter.encounter_id = "boss-1"
    encounter.run_id = "run-1"
    store = JsonStore(data_dir)

    saved = asyncio.run(store.create_mystic_encounter(encounter))
    restored = asyncio.run(JsonStore(data_dir).get_mystic_encounter("boss-1"))

    assert restored == saved
    assert [item.encounter_id for item in asyncio.run(store.list_active_mystic_encounters())] == ["boss-1"]


def test_encounter_compare_and_swap_rejects_stale_revision(data_dir: Path) -> None:
    service = MysticBattleService(mystic.default_mystic_gameplay_config(), now=lambda: NOW)
    encounter = service.create_boss_encounter(base_hp=500, member_ids=("a", "b"))
    encounter.encounter_id = "boss-1"
    store = JsonStore(data_dir)
    asyncio.run(store.create_mystic_encounter(encounter))

    first = asyncio.run(
        store.update_mystic_encounter("boss-1", 0, lambda item: item)
    )
    with pytest.raises(MysticEncounterConflict):
        asyncio.run(store.update_mystic_encounter("boss-1", 0, lambda item: item))

    assert first.revision == 1
    asyncio.run(store.delete_mystic_encounter("boss-1"))
    assert asyncio.run(store.get_mystic_encounter("boss-1")) is None


def test_rescue_take_delays_payout_until_success_and_restores_run(
    data_dir: Path,
    catalog: MysticTemplateCatalog,
) -> None:
    store = JsonStore(data_dir)
    leader = UserRecord(
        user_id="leader",
        spirit_stones=1_000,
        rewards=[token_reward()],
    )
    asyncio.run(store.save_user(leader))
    asyncio.run(store.save_user(UserRecord(user_id="member-2")))
    asyncio.run(store.save_user(UserRecord(user_id="rescuer")))
    run = started_team_run(catalog)
    saved = asyncio.run(
        store.create_mystic_run(run, payer_id="leader", token_name=NORMAL_TOKEN)
    )

    def block_for_rescue(item: MysticDungeonRun) -> MysticDungeonRun:
        item.phase = DungeonPhase.AWAITING_RESCUE
        item.active_encounter_id = "encounter-1"
        return item

    blocked = asyncio.run(
        store.update_mystic_run(saved.run_id, saved.revision, block_for_rescue)
    )
    request = MysticRescueRequest(
        request_id="rescue-1",
        run_id=blocked.run_id,
        encounter_id="encounter-1",
        group_id="100",
        requester_id="leader",
        requester_name="Leader",
        reward_stones=600,
        monster_snapshot={"user_id": "monster"},
        remaining_hp=250,
        deadline="2026-07-16T12:30:00",
    )

    asyncio.run(store.create_rescue_request(request))
    taken = asyncio.run(store.take_rescue_request("100", "rescue-1", "rescuer"))
    before = asyncio.run(store.get_user("rescuer"))
    completed = asyncio.run(store.complete_rescue_request("rescue-1", "rescuer"))
    asyncio.run(store.complete_rescue_request("rescue-1", "rescuer"))
    after = asyncio.run(store.get_user("rescuer"))
    restored = asyncio.run(store.get_mystic_run(blocked.run_id))
    payer = asyncio.run(store.get_user("leader"))

    assert taken is not None
    assert before.spirit_stones == 0
    assert completed.status == "completed"
    assert after.spirit_stones == 600
    assert payer.spirit_stones == 400
    assert restored is not None
    assert restored.phase is DungeonPhase.READY_TO_ROLL
    assert restored.active_encounter_id is None
    assert restored.current_node_id in restored.cleared_node_ids
